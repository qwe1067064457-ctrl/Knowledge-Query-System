from __future__ import annotations

import json

from retrieval_infra.indexing.repo_knowledge_manager import RepoKnowledgeIndexManager
from retrieval_infra.query.reranker import LocalCrossEncoderReranker

from knowledge_retrieval.types import Evidence, HybridRetrievalResult


class RepoKnowledgeRetriever:
    """直接基于 retrieval_infra 的 knowledge 检索器。"""

    def __init__(self, backend_dir=None) -> None:
        self.manager = RepoKnowledgeIndexManager(backend_dir=backend_dir)
        self.reranker = LocalCrossEncoderReranker()

    def retrieve(
        self,
        query: str,
        *,
        top_k: int = 4,
        path_filters: list[str] | None = None,
        query_hints: list[str] | None = None,
    ) -> HybridRetrievalResult:
        del query_hints
        vector_hits: list[Evidence] = []
        bm25_hits: list[Evidence] = []
        for group_id in self.manager._discover_groups():
            assets = self.manager.ensure_group_built(group_id)
            vector_scores = assets.vector.query(query, top_k=max(top_k * 2, top_k))
            lexical_scores = assets.lexical.query(query, top_k=max(top_k * 2, top_k))
            vector_hits.extend(self._to_evidences(vector_scores, assets.chunk_meta, assets.chunk_store, path_filters, channel="vector"))
            bm25_hits.extend(self._to_evidences(lexical_scores, assets.chunk_meta, assets.chunk_store, path_filters, channel="bm25"))
        vector_hits.sort(key=lambda item: item.score or 0.0, reverse=True)
        bm25_hits.sort(key=lambda item: item.score or 0.0, reverse=True)
        merged = self._dedupe_and_merge(vector_hits, bm25_hits)
        reranked = self.reranker.rerank(query, merged, top_k=top_k)
        reranked_ids = {(item.source_path, item.locator) for item in reranked}
        reranked_vector = [item for item in vector_hits if (item.source_path, item.locator) in reranked_ids][:top_k]
        reranked_bm25 = [item for item in bm25_hits if (item.source_path, item.locator) in reranked_ids][:top_k]
        return HybridRetrievalResult(vector_evidences=reranked_vector, bm25_evidences=reranked_bm25)

    def status(self):
        return self.manager.status()

    def is_building(self) -> bool:
        return self.manager.is_building()

    def rebuild_index(self) -> None:
        self.manager.rebuild_index()

    def configure(self, backend_dir) -> None:
        self.manager.configure(backend_dir)

    def _to_evidences(self, hits, chunk_meta, chunk_store, path_filters, *, channel: str) -> list[Evidence]:
        payload: list[Evidence] = []
        for chunk_id, score in hits:
            meta = chunk_meta.get(chunk_id)
            if not meta:
                continue
            source_path = str(meta["source_path"])
            if not self._matches_path_filters(source_path, path_filters):
                continue
            content = chunk_store.get_chunk_content(chunk_id) or ""
            payload.append(
                Evidence(
                    source_path=source_path,
                    source_type=str(meta["file_type"]),
                    locator=self._format_locator(meta["locator"]),
                    snippet=content,
                    channel=channel,  # type: ignore[arg-type]
                    score=score,
                    parent_id=str(meta["doc_id"]),
                )
            )
        return payload

    def _matches_path_filters(self, source_path: str, path_filters: list[str] | None) -> bool:
        if not path_filters:
            return True
        normalized = source_path.replace("\\", "/")
        for path_filter in path_filters:
            candidate = path_filter.replace("\\", "/").strip()
            if candidate and (normalized == candidate or normalized.startswith(f"{candidate}/")):
                return True
        return False

    def _format_locator(self, locator: object) -> str:
        if isinstance(locator, dict):
            if "page_no" in locator:
                return f"page:{locator['page_no']} chunk:{locator.get('chunk_index', 0)}"
            if "section" in locator:
                return str(locator["section"])
            if "paragraph_index" in locator:
                return f"paragraph:{locator['paragraph_index']} chunk:{locator.get('chunk_index', 0)}"
            return json.dumps(locator, ensure_ascii=False)
        return str(locator)

    def _dedupe_and_merge(self, vector_hits: list[Evidence], bm25_hits: list[Evidence]) -> list[Evidence]:
        merged: dict[tuple[str, str], Evidence] = {}
        for item in [*vector_hits, *bm25_hits]:
            key = (item.source_path, item.locator)
            existing = merged.get(key)
            if existing is None or (item.score or 0.0) > (existing.score or 0.0):
                merged[key] = item
        return list(merged.values())
