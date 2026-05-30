from __future__ import annotations

from retrieval_infra.contracts import SourceDocument


class KnowledgeSourceAdapter:
    def build_source_document(
        self,
        *,
        source_id: str,
        group_id: str,
        source_path: str,
        content: str,
        file_type: str,
        metadata: dict[str, object] | None = None,
        revision: str | None = None,
    ) -> SourceDocument:
        return SourceDocument(
            source_id=source_id,
            group_id=group_id,
            user_id=None,
            namespace="knowledge",
            source_kind="knowledge",
            source_path=source_path,
            file_type=file_type,
            content=content,
            metadata=metadata or {},
            revision=revision,
        )
