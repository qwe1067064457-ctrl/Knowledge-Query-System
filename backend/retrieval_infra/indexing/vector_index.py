from __future__ import annotations

import json
import math
import re
import sqlite3
from collections import Counter
from pathlib import Path

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


class SimpleVectorIndex:
    """持久化稀疏向量召回后端。

    不绑定外部 embedding 服务，先用 token tf-idf 稀疏向量做稳定召回，
    保留 `vector/` 目录与查询接口，后续可无缝替换为真实 dense embedding backend。
    """

    def __init__(self, db_path: Path) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(_sqlite_path(self.db_path)) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS vectors (
                    chunk_id TEXT PRIMARY KEY,
                    weights_json TEXT NOT NULL
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
        doc_freq: Counter[str] = Counter()
        chunk_counters: list[tuple[str, Counter[str]]] = []
        for chunk in chunks:
            counter = Counter(_tokenize(chunk.content))
            if not counter:
                continue
            chunk_counters.append((chunk.chunk_id, counter))
            for term in counter:
                doc_freq[term] += 1
        total_docs = max(1, len(chunk_counters))
        with sqlite3.connect(_sqlite_path(self.db_path)) as conn:
            conn.execute("DELETE FROM vectors")
            conn.execute("DELETE FROM vector_globals")
            conn.executemany(
                "INSERT INTO vectors(chunk_id, weights_json) VALUES (?, ?)",
                [
                    (
                        chunk_id,
                        json.dumps(self._build_weights(counter, doc_freq, total_docs), ensure_ascii=False),
                    )
                    for chunk_id, counter in chunk_counters
                ],
            )
            conn.executemany(
                "INSERT INTO vector_globals(key, value) VALUES (?, ?)",
                [
                    ("total_docs", str(total_docs)),
                    ("doc_freq", json.dumps(doc_freq, ensure_ascii=False)),
                ],
            )
            conn.commit()

    def query(self, text: str, *, top_k: int = 5) -> list[tuple[str, float]]:
        query_counter = Counter(_tokenize(text))
        if not query_counter:
            return []
        scores: list[tuple[str, float]] = []
        with sqlite3.connect(_sqlite_path(self.db_path)) as conn:
            globals_rows = dict(conn.execute("SELECT key, value FROM vector_globals").fetchall())
            total_docs = int(globals_rows.get("total_docs") or "1")
            doc_freq = Counter(json.loads(globals_rows.get("doc_freq") or "{}"))
            query_weights = self._build_weights(query_counter, doc_freq, total_docs)
            query_norm = self._norm(query_weights)
            if query_norm <= 0:
                return []
            for chunk_id, weights_json in conn.execute("SELECT chunk_id, weights_json FROM vectors").fetchall():
                chunk_weights = json.loads(weights_json)
                chunk_norm = self._norm(chunk_weights)
                if chunk_norm <= 0:
                    continue
                dot = sum(float(query_weights.get(term, 0.0)) * float(chunk_weights.get(term, 0.0)) for term in query_weights.keys())
                if dot <= 0:
                    continue
                scores.append((str(chunk_id), dot / (query_norm * chunk_norm)))
        scores.sort(key=lambda item: item[1], reverse=True)
        return scores[:top_k]

    def _build_weights(self, counter: Counter[str], doc_freq: Counter[str], total_docs: int) -> dict[str, float]:
        weights: dict[str, float] = {}
        max_tf = max(counter.values()) if counter else 1
        for term, tf in counter.items():
            df = doc_freq.get(term, 0)
            idf = math.log(1 + ((total_docs - df + 0.5) / (df + 0.5))) if df else 0.0
            weights[term] = round((0.5 + 0.5 * (tf / max_tf)) * idf, 6)
        return weights

    def _norm(self, weights: dict[str, float]) -> float:
        return math.sqrt(sum(float(value) * float(value) for value in weights.values()))
