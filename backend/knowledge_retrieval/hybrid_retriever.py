from __future__ import annotations

from retrieval_infra.query.repo_knowledge_retriever import RepoKnowledgeRetriever
from knowledge_retrieval.types import HybridRetrievalResult


class HybridRetriever:
    def __init__(self) -> None:
        self.repo_retriever = RepoKnowledgeRetriever()

    def retrieve(
        self,
        query: str,
        *,
        top_k: int = 4,
        path_filters: list[str] | None = None,
        query_hints: list[str] | None = None,
    ) -> HybridRetrievalResult:
        return self.repo_retriever.retrieve(
            query,
            top_k=top_k,
            path_filters=path_filters,
            query_hints=query_hints,
        )


hybrid_retriever = HybridRetriever()
