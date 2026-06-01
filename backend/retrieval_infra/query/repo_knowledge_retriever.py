from __future__ import annotations

import json
from collections import defaultdict

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
        text_hits: list[Evidence] = []
        table_hits: list[Evidence] = []
        for group_id in self.manager._discover_groups():
            assets = self.manager.ensure_group_built(group_id)
            text_vector_scores = assets.text_vector.query(query, top_k=max(top_k * 3, top_k))
            text_lexical_scores = assets.text_lexical.query(query, top_k=max(top_k * 3, top_k))
            table_vector_scores = assets.table_vector.query(query, top_k=max(3, top_k))
            table_lexical_scores = assets.table_lexical.query(query, top_k=max(3, top_k))

            text_vector_hits = self._to_evidences(text_vector_scores, assets.chunk_meta, assets.chunk_store, path_filters, channel="vector", pool="text")
            text_bm25_hits = self._to_evidences(text_lexical_scores, assets.chunk_meta, assets.chunk_store, path_filters, channel="bm25", pool="text")
            table_vector_hits = self._to_evidences(table_vector_scores, assets.chunk_meta, assets.chunk_store, path_filters, channel="vector", pool="table")
            table_bm25_hits = self._to_evidences(table_lexical_scores, assets.chunk_meta, assets.chunk_store, path_filters, channel="bm25", pool="table")

            vector_hits.extend([*text_vector_hits, *table_vector_hits])
            bm25_hits.extend([*text_bm25_hits, *table_bm25_hits])
            text_hits.extend([*text_vector_hits, *text_bm25_hits])
            table_hits.extend([*table_vector_hits, *table_bm25_hits])
        vector_hits.sort(key=lambda item: item.score or 0.0, reverse=True)
        bm25_hits.sort(key=lambda item: item.score or 0.0, reverse=True)
        merged = self._rrf_merge(
            [
                text_hits[: max(top_k * 3, top_k * 2)],
                table_hits[: max(3, top_k)],
                vector_hits[: max(top_k * 3, top_k * 2)],
                bm25_hits[: max(top_k * 3, top_k * 2)],
            ]
        )
        reranked = self.reranker.rerank(query, merged, top_k=top_k)
        reranked_ids = {(item.source_path, item.locator) for item in reranked}
        reranked_vector = [item for item in vector_hits if (item.source_path, item.locator) in reranked_ids][:top_k]
        reranked_bm25 = [item for item in bm25_hits if (item.source_path, item.locator) in reranked_ids][:top_k]
        reranked_text = [item for item in text_hits if (item.source_path, item.locator) in reranked_ids][:top_k]
        reranked_table = [item for item in table_hits if (item.source_path, item.locator) in reranked_ids][:top_k]
        return HybridRetrievalResult(
            vector_evidences=reranked_vector,
            bm25_evidences=reranked_bm25,
            text_hits=reranked_text,
            table_hits=reranked_table,
            merged_hits=reranked,
        )

    def status(self):
        return self.manager.status()

    def is_building(self) -> bool:
        return self.manager.is_building()

    def rebuild_index(self) -> None:
        self.manager.rebuild_index()

    def configure(self, backend_dir) -> None:
        self.manager.configure(backend_dir)

    def _to_evidences(self, hits, chunk_meta, chunk_store, path_filters, *, channel: str, pool: str) -> list[Evidence]:
        payload: list[Evidence] = []
        for chunk_id, score in hits:
            meta = chunk_meta.get(chunk_id)
            if not meta:
                continue
            if str(meta.get("pool") or "") != pool:
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
                    metadata={
                        "pool": pool,
                        "structured_only": bool(meta.get("structured_only")),
                        "analysis_available": bool(meta.get("analysis_available")),
                    },
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

    def _rrf_merge(self, channels: list[list[Evidence]], *, k: int = 60) -> list[Evidence]:
        fused_scores: defaultdict[tuple[str, str], float] = defaultdict(float)
        representative: dict[tuple[str, str], Evidence] = {}
        for channel_hits in channels:
            for rank, item in enumerate(channel_hits, start=1):
                key = (item.source_path, item.locator)
                fused_scores[key] += 1.0 / (k + rank)
                if key not in representative or (item.score or 0.0) > (representative[key].score or 0.0):
                    representative[key] = item
        merged: list[Evidence] = []
        for key, evidence in representative.items():
            evidence.score = max(float(evidence.score or 0.0), fused_scores[key])
            evidence.channel = "fused"
            merged.append(evidence)
        merged.sort(key=lambda item: item.score or 0.0, reverse=True)
        return merged
