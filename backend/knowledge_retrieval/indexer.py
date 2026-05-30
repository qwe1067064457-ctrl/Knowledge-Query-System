from __future__ import annotations

from pathlib import Path

from retrieval_infra.query.repo_knowledge_retriever import RepoKnowledgeRetriever

from knowledge_retrieval.types import Evidence, IndexStatus


class KnowledgeIndexer:
    """兼容旧接口的 facade，底层直接走 retrieval_infra。"""

    def __init__(self) -> None:
        self.retriever = RepoKnowledgeRetriever()

    def configure(self, base_dir: Path) -> None:
        self.retriever.configure(base_dir)

    def status(self) -> IndexStatus:
        return self.retriever.status()

    def is_building(self) -> bool:
        return self.retriever.is_building()

    def rebuild_index(self) -> None:
        self.retriever.rebuild_index()

    def retrieve_vector(
        self,
        query: str,
        *,
        top_k: int = 4,
        path_filters: list[str] | None = None,
    ) -> list[Evidence]:
        result = self.retriever.retrieve(query, top_k=top_k, path_filters=path_filters)
        return result.vector_evidences

    def retrieve_bm25(
        self,
        query: str,
        *,
        top_k: int = 4,
        path_filters: list[str] | None = None,
        query_hints: list[str] | None = None,
    ) -> list[Evidence]:
        result = self.retriever.retrieve(query, top_k=top_k, path_filters=path_filters, query_hints=query_hints)
        return result.bm25_evidences


knowledge_indexer = KnowledgeIndexer()
