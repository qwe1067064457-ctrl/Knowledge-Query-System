from __future__ import annotations

import hashlib
import json
import math
import os
import re
import sqlite3
from collections import Counter
from pathlib import Path
from typing import Protocol

import httpx

from config import get_settings
from retrieval_infra.contracts import ChunkDocument


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[\u4e00-\u9fff]|[A-Za-z0-9_]+", text.lower())


def _sqlite_path(path: Path) -> str:
    resolved = path.resolve()
    raw = str(resolved)
    if raw.startswith("\\\\?\\"):
        return raw
    if len(raw) >= 240 and resolved.drive:
        return f"\\\\?\\{raw}"
    return raw


class _EmbeddingBackend(Protocol):
    backend_name: str

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        ...


class _HashEmbeddingBackend:
    """Offline/test fallback so indexing stays deterministic without remote calls."""

    backend_name = "hash_fallback"

    def __init__(self, *, dim: int = 4096) -> None:
        self.dim = dim

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [self._embed_one(text) for text in texts]

    def _embed_one(self, text: str) -> list[float]:
        buckets = [0.0] * self.dim
        for token, count in Counter(_tokenize(text)).items():
            digest = hashlib.md5(token.encode("utf-8")).digest()
            slot = int.from_bytes(digest[:4], "big") % self.dim
            sign = -1.0 if digest[4] % 2 else 1.0
            buckets[slot] += sign * float(count)
        norm = math.sqrt(sum(value * value for value in buckets))
        if norm <= 0:
            return buckets
        return [round(value / norm, 8) for value in buckets]


class _RemoteEmbeddingBackend:
    backend_name = "remote_api"

    def __init__(self) -> None:
        settings = get_settings()
        self.base_url = settings.embedding_base_url.rstrip("/")
        self.model = settings.embedding_model
        self.api_key = settings.embedding_api_key or ""
        self.timeout = 60.0

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        response = httpx.post(
            f"{self.base_url}/embeddings",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.model,
                "input": texts,
            },
            timeout=self.timeout,
        )
        response.raise_for_status()
        payload = response.json()
        rows = list(payload.get("data", []) or [])
        embeddings = [list(item.get("embedding", []) or []) for item in rows]
        if len(embeddings) != len(texts):
            raise ValueError("embedding response size mismatch")
        return [[float(value) for value in item] for item in embeddings]


class EmbeddingVectorIndex:
    """Dense vector recall backed by the configured embedding model.

    The on-disk `vector/` slot now stores real dense vectors. Tests and offline
    environments fall back to a deterministic local hash embedder.
    """

    def __init__(self, db_path: Path, *, backend: _EmbeddingBackend | None = None) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.backend = backend or self._default_backend()
        self._legacy_sparse_schema = False
        with sqlite3.connect(_sqlite_path(self.db_path)) as conn:
            table_exists = conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='vectors'"
            ).fetchone()
            columns = {row[1] for row in conn.execute("PRAGMA table_info(vectors)").fetchall()} if table_exists else set()
            if "weights_json" in columns and "vector_json" not in columns:
                self._legacy_sparse_schema = True
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS vectors (
                    chunk_id TEXT PRIMARY KEY,
                    vector_json TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS vector_globals (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
                """
            )
            conn.commit()

    def rebuild(self, chunks: tuple[ChunkDocument, ...]) -> None:
        embedding_texts: list[str] = []
        chunk_ids: list[str] = []
        for chunk in chunks:
            text = self._build_embedding_text(chunk)
            if not text:
                continue
            chunk_ids.append(chunk.chunk_id)
            embedding_texts.append(text)
        vectors = self.backend.embed_texts(embedding_texts)
        dimension = len(vectors[0]) if vectors else 0
        with sqlite3.connect(_sqlite_path(self.db_path)) as conn:
            if self._legacy_sparse_schema:
                conn.execute("DROP TABLE IF EXISTS vectors")
                conn.execute("DROP TABLE IF EXISTS vector_globals")
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS vectors (
                        chunk_id TEXT PRIMARY KEY,
                        vector_json TEXT NOT NULL
                    )
                    """
                )
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS vector_globals (
                        key TEXT PRIMARY KEY,
                        value TEXT NOT NULL
                    )
                    """
                )
                self._legacy_sparse_schema = False
            conn.execute("DELETE FROM vectors")
            conn.execute("DELETE FROM vector_globals")
            conn.executemany(
                "INSERT INTO vectors(chunk_id, vector_json) VALUES (?, ?)",
                [
                    (chunk_id, json.dumps(vector, ensure_ascii=False))
                    for chunk_id, vector in zip(chunk_ids, vectors)
                ],
            )
            conn.executemany(
                "INSERT INTO vector_globals(key, value) VALUES (?, ?)",
                [
                    ("dimension", str(dimension)),
                    ("backend", self.backend.backend_name),
                ],
            )
            conn.commit()

    def query(self, text: str, *, top_k: int = 5) -> list[tuple[str, float]]:
        query_text = text.strip()
        if not query_text:
            return []
        if self._legacy_sparse_schema:
            return self._query_legacy_sparse(query_text, top_k=top_k)
        query_vector = self.backend.embed_texts([query_text])[0]
        query_norm = self._norm(query_vector)
        if query_norm <= 0:
            return []
        scores: list[tuple[str, float]] = []
        with sqlite3.connect(_sqlite_path(self.db_path)) as conn:
            for chunk_id, vector_json in conn.execute("SELECT chunk_id, vector_json FROM vectors").fetchall():
                chunk_vector = [float(value) for value in json.loads(vector_json)]
                chunk_norm = self._norm(chunk_vector)
                if chunk_norm <= 0:
                    continue
                dot = sum(left * right for left, right in zip(query_vector, chunk_vector))
                score = dot / (query_norm * chunk_norm)
                if score <= 0:
                    continue
                scores.append((str(chunk_id), round(score, 6)))
        scores.sort(key=lambda item: item[1], reverse=True)
        return scores[:top_k]

    def _build_embedding_text(self, chunk: ChunkDocument) -> str:
        metadata = dict(chunk.metadata)
        signal_parts: list[str] = []
        for value in metadata.get("retrieval_signals", []) or ():
            text = str(value).strip()
            if text:
                signal_parts.append(text)
        heading = str(metadata.get("heading") or "").strip()
        if heading:
            signal_parts.append(heading)
        locator = " ".join(
            str(value).strip()
            for value in chunk.locator.values()
            if isinstance(value, (str, int, float)) and str(value).strip()
        )
        parts = [part for part in [*signal_parts, locator, chunk.content.strip()] if part]
        return "\n".join(parts).strip()

    def _default_backend(self) -> _EmbeddingBackend:
        settings = get_settings()
        force_local = os.getenv("PYTEST_CURRENT_TEST") or not settings.embedding_api_key
        if force_local:
            return _HashEmbeddingBackend()
        return _RemoteEmbeddingBackend()

    @staticmethod
    def _norm(vector: list[float]) -> float:
        return math.sqrt(sum(float(value) * float(value) for value in vector))

    def _query_legacy_sparse(self, text: str, *, top_k: int) -> list[tuple[str, float]]:
        query_counter = Counter(_tokenize(text))
        if not query_counter:
            return []
        scores: list[tuple[str, float]] = []
        with sqlite3.connect(_sqlite_path(self.db_path)) as conn:
            globals_rows = dict(conn.execute("SELECT key, value FROM vector_globals").fetchall())
            total_docs = int(globals_rows.get("total_docs") or "1")
            doc_freq = Counter(json.loads(globals_rows.get("doc_freq") or "{}"))
            query_weights = self._build_legacy_weights(query_counter, doc_freq, total_docs)
            query_norm = math.sqrt(sum(float(value) * float(value) for value in query_weights.values()))
            if query_norm <= 0:
                return []
            for chunk_id, weights_json in conn.execute("SELECT chunk_id, weights_json FROM vectors").fetchall():
                chunk_weights = json.loads(weights_json)
                chunk_norm = math.sqrt(sum(float(value) * float(value) for value in chunk_weights.values()))
                if chunk_norm <= 0:
                    continue
                dot = sum(float(query_weights.get(term, 0.0)) * float(chunk_weights.get(term, 0.0)) for term in query_weights.keys())
                if dot <= 0:
                    continue
                scores.append((str(chunk_id), round(dot / (query_norm * chunk_norm), 6)))
        scores.sort(key=lambda item: item[1], reverse=True)
        return scores[:top_k]

    def _build_legacy_weights(self, counter: Counter[str], doc_freq: Counter[str], total_docs: int) -> dict[str, float]:
        weights: dict[str, float] = {}
        max_tf = max(counter.values()) if counter else 1
        for term, tf in counter.items():
            df = doc_freq.get(term, 0)
            idf = math.log(1 + ((total_docs - df + 0.5) / (df + 0.5))) if df else 0.0
            weights[term] = round((0.5 + 0.5 * (tf / max_tf)) * idf, 6)
        return weights


# Backward-compatible export name used across the current retrieval code/tests.
SimpleVectorIndex = EmbeddingVectorIndex
