from __future__ import annotations

import json
import re
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
        query_text = self._merge_query_inputs(query, query_hints)
        vector_hits: list[Evidence] = []
        bm25_hits: list[Evidence] = []
        text_hits: list[Evidence] = []
        table_hits: list[Evidence] = []
        auxiliary_text_hits: list[Evidence] = []
        for group_id in self.manager._discover_groups():
            assets = self.manager.ensure_group_built(group_id)
            text_vector_scores = assets.text_vector.query(query_text, top_k=max(top_k * 3, top_k))
            text_lexical_scores = assets.text_lexical.query(query_text, top_k=max(top_k * 3, top_k))
            table_vector_scores = assets.table_vector.query(query_text, top_k=max(3, top_k))
            table_lexical_scores = assets.table_lexical.query(query_text, top_k=max(3, top_k))

            text_vector_hits = self._to_evidences(text_vector_scores, assets.chunk_meta, assets.chunk_store, path_filters, channel="vector", pool="text")
            text_bm25_hits = self._to_evidences(text_lexical_scores, assets.chunk_meta, assets.chunk_store, path_filters, channel="bm25", pool="text")
            table_vector_hits = self._to_evidences(table_vector_scores, assets.chunk_meta, assets.chunk_store, path_filters, channel="vector", pool="table")
            table_bm25_hits = self._to_evidences(table_lexical_scores, assets.chunk_meta, assets.chunk_store, path_filters, channel="bm25", pool="table")

            primary_text_vector_hits, aux_text_vector_hits = self._split_auxiliary_hits(text_vector_hits)
            primary_text_bm25_hits, aux_text_bm25_hits = self._split_auxiliary_hits(text_bm25_hits)

            vector_hits.extend([*primary_text_vector_hits, *table_vector_hits])
            bm25_hits.extend([*primary_text_bm25_hits, *table_bm25_hits])
            text_hits.extend([*primary_text_vector_hits, *primary_text_bm25_hits])
            table_hits.extend([*table_vector_hits, *table_bm25_hits])
            auxiliary_text_hits.extend([*aux_text_vector_hits, *aux_text_bm25_hits])
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
        if not merged and auxiliary_text_hits:
            merged = self._append_auxiliary_fallbacks(
                merged,
                auxiliary_text_hits[: max(top_k * 3, top_k * 2)],
                limit=top_k,
            )
        reranked = self.reranker.rerank(query_text, merged, top_k=top_k)
        reranked_ids = {(item.source_path, item.locator) for item in reranked}
        reranked_vector = [item for item in vector_hits if (item.source_path, item.locator) in reranked_ids][:top_k]
        reranked_bm25 = [item for item in bm25_hits if (item.source_path, item.locator) in reranked_ids][:top_k]
        reranked_text = [item for item in [*text_hits, *auxiliary_text_hits] if (item.source_path, item.locator) in reranked_ids][:top_k]
        reranked_table = [item for item in table_hits if (item.source_path, item.locator) in reranked_ids][:top_k]
        return HybridRetrievalResult(
            vector_evidences=reranked_vector,
            bm25_evidences=reranked_bm25,
            text_hits=reranked_text,
            table_hits=reranked_table,
            merged_hits=reranked,
        )

    def status(self, group_id: str | None = None):
        return self.manager.status(group_id=group_id)

    def is_building(self) -> bool:
        return self.manager.is_building()

    def rebuild_index(self, group_id: str | None = None) -> None:
        self.manager.rebuild_index(group_id=group_id)

    def configure(self, backend_dir) -> None:
        self.manager.configure(backend_dir)

    def list_groups(self) -> list[str]:
        return self.manager.list_groups()

    def count_group_sources(self, group_id: str) -> int:
        return self.manager.count_group_sources(group_id)

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
                        "source_role": self._source_role(source_path),
                    },
                )
            )
        return payload

    def _split_auxiliary_hits(self, hits: list[Evidence]) -> tuple[list[Evidence], list[Evidence]]:
        primary: list[Evidence] = []
        auxiliary: list[Evidence] = []
        for item in hits:
            if self._is_auxiliary_evidence(item):
                auxiliary.append(item)
            else:
                primary.append(item)
        return primary, auxiliary

    def _append_auxiliary_fallbacks(self, merged: list[Evidence], auxiliary_hits: list[Evidence], *, limit: int) -> list[Evidence]:
        combined = list(merged)
        existing_keys = {self._evidence_identity_key(item) for item in merged}
        for item in auxiliary_hits:
            key = self._evidence_identity_key(item)
            if key in existing_keys:
                continue
            existing_keys.add(key)
            combined.append(item)
            if len(combined) >= limit:
                break
        return combined

    def _is_auxiliary_evidence(self, evidence: Evidence) -> bool:
        return self._source_role(evidence.source_path) == "auxiliary"

    def _source_role(self, source_path: str) -> str:
        name = source_path.replace("\\", "/").rsplit("/", 1)[-1].lower()
        if name in {"metadata.json", "manifest.json", "index.md", "readme.md"}:
            return "auxiliary"
        return "primary"

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
                key = self._evidence_identity_key(item)
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

    def _merge_query_inputs(self, query: str, query_hints: list[str] | None) -> str:
        hints = [str(item).strip() for item in query_hints or [] if str(item).strip()]
        if not hints:
            return query
        return "\n".join([query.strip(), *hints]).strip()

    def _evidence_identity_key(self, evidence: Evidence) -> tuple[str, str]:
        snippet = re.sub(r"\s+", " ", evidence.snippet or "").strip().lower()
        if len(snippet) >= 80:
            return ("snippet", snippet[:240])
        parent = str(evidence.parent_id or evidence.source_path)
        if snippet:
            return (parent, snippet[:240])
        return (parent, evidence.locator)
