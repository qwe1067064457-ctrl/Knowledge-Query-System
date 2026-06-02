from __future__ import annotations

import hashlib
import json
from pathlib import Path

from context.models import MemoryEntry
from retrieval_infra.indexing import ChunkStore, LexicalIndex, SimpleVectorIndex


class MemoryHybridRetriever:
    def __init__(self, base_storage_path: Path) -> None:
        self.base_storage_path = Path(base_storage_path)

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
        if not (slot_dir / "chunk_store.sqlite").exists():
            return []
        lexical_dir = slot_dir / "lexical"
        vector_dir = slot_dir / "vector"
        lexical = LexicalIndex(lexical_dir / "term_postings.sqlite", lexical_dir / "globals.json")
        vector = SimpleVectorIndex(vector_dir / "index.sqlite")
        chunk_store = ChunkStore(slot_dir / "chunk_store.sqlite")
        meta_path = slot_dir / "chunk_meta.json"
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

    def _entry_id(self, entry: MemoryEntry) -> str:
        if entry.metadata and entry.metadata.get("id"):
            return str(entry.metadata["id"])
        return hashlib.md5(f"{entry.memory_type}:{entry.group_id}:{entry.user_id}:{entry.title}:{entry.content}".encode("utf-8")).hexdigest()
