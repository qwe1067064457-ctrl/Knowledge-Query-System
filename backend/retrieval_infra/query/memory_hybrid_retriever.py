from __future__ import annotations

import hashlib
import json
from pathlib import Path

from context.models import MemoryEntry
from retrieval_infra.adapters import MemorySourceAdapter
from retrieval_infra.chunking import TextChunker
from retrieval_infra.indexing import ChunkStore, LexicalIndex, SimpleVectorIndex
from retrieval_infra.normalization import DocumentNormalizer
from retrieval_infra.parsing import SimpleTextParser


class MemoryHybridRetriever:
    def __init__(self, base_storage_path: Path) -> None:
        self.base_storage_path = Path(base_storage_path)
        self.adapter = MemorySourceAdapter()
        self.parser = SimpleTextParser()
        self.normalizer = DocumentNormalizer()
        self.chunker = TextChunker()

    def retrieve(
        self,
        *,
        group_id: str,
        user_id: str,
        query: str,
        memory_entries: list[MemoryEntry],
        top_k: int = 5,
    ) -> list[MemoryEntry]:
        slot_dir = self.base_storage_path / "groups" / group_id / "users" / user_id / "indexes" / "memory" / "current"
        lexical_dir = slot_dir / "lexical"
        vector_dir = slot_dir / "vector"
        lexical = LexicalIndex(lexical_dir / "term_postings.sqlite", lexical_dir / "globals.json")
        vector = SimpleVectorIndex(vector_dir / "index.sqlite")
        chunk_store = ChunkStore(slot_dir / "chunk_store.sqlite")
        meta_path = slot_dir / "chunk_meta.json"
        fingerprint_path = slot_dir / "build_fingerprint.json"

        fingerprint = self._fingerprint(memory_entries)
        if fingerprint_path.read_text(encoding="utf-8") if fingerprint_path.exists() else "" != fingerprint:
            chunks = self._build_chunks(memory_entries)
            chunk_store.upsert_chunks(chunks)
            lexical.rebuild(chunks)
            vector.rebuild(chunks)
            chunk_meta = {
                chunk.chunk_id: {
                    "source": chunk.source_path,
                    "memory_id": chunk.metadata.get("memory_id"),
                    "memory_type": chunk.metadata.get("memory_type"),
                }
                for chunk in chunks
            }
            meta_path.write_text(json.dumps(chunk_meta, ensure_ascii=False, indent=2), encoding="utf-8")
            fingerprint_path.write_text(fingerprint, encoding="utf-8")

        chunk_meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
        scored: dict[str, float] = {}
        for chunk_id, score in lexical.query(query, top_k=max(top_k * 3, top_k)):
            scored[chunk_id] = max(scored.get(chunk_id, 0.0), score)
        for chunk_id, score in vector.query(query, top_k=max(top_k * 3, top_k)):
            scored[chunk_id] = max(scored.get(chunk_id, 0.0), score)

        entries_by_id = {str(entry.metadata.get("id") if entry.metadata else "") or self._entry_id(entry): entry for entry in memory_entries}
        resolved: list[MemoryEntry] = []
        seen_ids: set[str] = set()
        for chunk_id, score in sorted(scored.items(), key=lambda item: item[1], reverse=True):
            memory_id = str((chunk_meta.get(chunk_id) or {}).get("memory_id") or "")
            entry = entries_by_id.get(memory_id)
            if entry is None or memory_id in seen_ids:
                continue
            entry.score = max(entry.score, score)
            resolved.append(entry)
            seen_ids.add(memory_id)
            if len(resolved) >= top_k:
                break
        return resolved

    def _build_chunks(self, entries: list[MemoryEntry]):
        chunks = []
        for entry in entries:
            memory_id = self._entry_id(entry)
            source = self.adapter.build_source_document(
                source_id=memory_id,
                group_id=entry.group_id,
                user_id=entry.user_id or "default",
                source_kind=entry.memory_type,
                source_path=entry.source,
                content=f"{entry.title or ''}\n{entry.subject or ''}\n{entry.content}".strip(),
                metadata={
                    "title": entry.title or entry.subject or entry.memory_type,
                    "memory_id": memory_id,
                    "memory_type": entry.memory_type,
                },
                revision=entry.timestamp.isoformat(),
            )
            parsed = self.parser.parse(f"doc_{memory_id}", source)
            normalized = self.normalizer.normalize(parsed)
            chunks.extend(self.chunker.chunk(normalized))
        return tuple(chunks)

    def _fingerprint(self, entries: list[MemoryEntry]) -> str:
        digest = hashlib.md5()
        for entry in sorted(entries, key=lambda item: (item.memory_type, item.timestamp.isoformat(), item.content)):
            digest.update(self._entry_id(entry).encode("utf-8"))
            digest.update(entry.timestamp.isoformat().encode("utf-8"))
            digest.update(entry.content.encode("utf-8"))
        return digest.hexdigest()

    def _entry_id(self, entry: MemoryEntry) -> str:
        if entry.metadata and entry.metadata.get("id"):
            return str(entry.metadata["id"])
        return hashlib.md5(f"{entry.memory_type}:{entry.group_id}:{entry.user_id}:{entry.title}:{entry.content}".encode("utf-8")).hexdigest()
