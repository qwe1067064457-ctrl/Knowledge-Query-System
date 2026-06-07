from __future__ import annotations

from retrieval_infra.contracts import NormalizedDocument, ParsedDocument


class DocumentNormalizer:
    def normalize(self, parsed: ParsedDocument) -> NormalizedDocument:
        return NormalizedDocument(
            doc_id=parsed.doc_id,
            group_id=parsed.source.group_id,
            user_id=parsed.source.user_id,
            namespace=parsed.source.namespace,
            source_kind=parsed.source.source_kind,
            source_path=parsed.source.source_path,
            file_type=parsed.source.file_type,
            title=parsed.title,
            sections=parsed.sections,
            metadata=dict(parsed.source.metadata),
            revision=parsed.source.revision,
        )
