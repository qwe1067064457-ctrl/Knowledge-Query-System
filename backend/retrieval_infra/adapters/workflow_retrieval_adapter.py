from __future__ import annotations

from pathlib import Path

from retrieval_infra.query.lexical_retriever import LexicalRetriever


class WorkflowRetrievalAdapter:
    """一期桥接层：让 workflow 先可消费新的 lexical index。"""

    def __init__(self, lexical_db_path: Path, globals_path: Path) -> None:
        self.retriever = LexicalRetriever(lexical_db_path, globals_path)

    def retrieve(self, query: str, *, top_k: int = 5) -> list[tuple[str, float]]:
        return self.retriever.retrieve(query, top_k=top_k)
