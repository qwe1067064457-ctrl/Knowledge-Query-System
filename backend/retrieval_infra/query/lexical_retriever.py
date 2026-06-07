from __future__ import annotations

from pathlib import Path

from retrieval_infra.indexing.lexical_index import LexicalIndex


class LexicalRetriever:
    def __init__(self, lexical_db_path: Path, globals_path: Path) -> None:
        self.index = LexicalIndex(lexical_db_path, globals_path)

    def retrieve(self, query: str, *, top_k: int = 5) -> list[tuple[str, float]]:
        return self.index.query(query, top_k=top_k)
