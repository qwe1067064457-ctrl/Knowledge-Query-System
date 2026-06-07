from __future__ import annotations

from retrieval_infra.contracts import SourceDocument


class MemorySourceAdapter:
    def build_source_document(
        self,
        *,
        source_id: str,
        group_id: str,
        user_id: str,
        source_kind: str,
        source_path: str,
        content: str,
        file_type: str = "memory_text",
        metadata: dict[str, object] | None = None,
        revision: str | None = None,
    ) -> SourceDocument:
        return SourceDocument(
            source_id=source_id,
            group_id=group_id,
            user_id=user_id,
            namespace="memory",
            source_kind=source_kind,  # type: ignore[arg-type]
            source_path=source_path,
            file_type=file_type,
            content=content,
            metadata=metadata or {},
            revision=revision,
        )
