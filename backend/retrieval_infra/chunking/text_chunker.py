from __future__ import annotations

import hashlib
import re

from retrieval_infra.contracts import ChunkDocument, NormalizedDocument


class TextChunker:
    """更细粒度 chunker。

    - markdown/html/json/docx/pdf：按 section 内部段落与长度进一步切分
    - excel：仅保留结构摘要块，不生成普通 prose chunk
    """

    def __init__(self, max_chars: int = 900) -> None:
        self.max_chars = max_chars

    def chunk(self, document: NormalizedDocument) -> tuple[ChunkDocument, ...]:
        chunks: list[ChunkDocument] = []
        chunk_index = 0
        for section_index, section in enumerate(document.sections):
            content = str(section.get("text") or "").strip()
            if not content:
                continue
            units = [content] if section.get("structured_only") else self._split_section(content)
            for unit in units:
                unit = unit.strip()
                if not unit:
                    continue
                seed = f"{document.doc_id}:{section_index}:{chunk_index}:{unit}".encode("utf-8")
                chunk_id = f"chunk_{hashlib.md5(seed).hexdigest()}"
                chunks.append(
                    ChunkDocument(
                        chunk_id=chunk_id,
                        doc_id=document.doc_id,
                        group_id=document.group_id,
                        user_id=document.user_id,
                        namespace=document.namespace,
                        source_kind=document.source_kind,
                        source_path=document.source_path,
                        file_type=document.file_type,
                        content=unit,
                        locator=dict(section.get("locator") or {}) | {"section_index": section_index, "chunk_index": chunk_index},
                        metadata=dict(document.metadata)
                        | {
                            "heading": section.get("heading"),
                            "structured_only": bool(section.get("structured_only")),
                            "analysis_available": bool(section.get("analysis_available", False)),
                            "field_roles": dict(section.get("field_roles") or {}),
                            "headers": list(section.get("headers") or []),
                            "row_count": int(section.get("row_count") or 0),
                            "preview_rows": list(section.get("preview_rows") or []),
                        },
                        revision=document.revision,
                    )
                )
                chunk_index += 1
        return tuple(chunks)

    def _split_section(self, content: str) -> list[str]:
        paragraphs = [part.strip() for part in re.split(r"\n{2,}", content) if part.strip()]
        if not paragraphs:
            paragraphs = [content.strip()]
        chunks: list[str] = []
        buffer = ""
        for paragraph in paragraphs:
            candidate = paragraph if not buffer else f"{buffer}\n\n{paragraph}"
            if len(candidate) <= self.max_chars:
                buffer = candidate
                continue
            if buffer:
                chunks.append(buffer)
            if len(paragraph) <= self.max_chars:
                buffer = paragraph
                continue
            sentences = [part.strip() for part in re.split(r"(?<=[。！？!?\.])\s+", paragraph) if part.strip()]
            running = ""
            for sentence in sentences or [paragraph]:
                candidate_sentence = sentence if not running else f"{running} {sentence}"
                if len(candidate_sentence) <= self.max_chars:
                    running = candidate_sentence
                    continue
                if running:
                    chunks.append(running)
                running = sentence
            buffer = running
        if buffer:
            chunks.append(buffer)
        return chunks
