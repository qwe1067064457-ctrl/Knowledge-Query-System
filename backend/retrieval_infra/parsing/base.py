from __future__ import annotations

import json
import re
from dataclasses import dataclass

from retrieval_infra.contracts import ParsedDocument, SourceDocument


@dataclass(frozen=True)
class ParsedSection:
    heading: str | None
    text: str
    locator: dict[str, object]


class SimpleTextParser:
    """文件类型感知 parser。"""

    def parse(self, doc_id: str, source: SourceDocument) -> ParsedDocument:
        parser = getattr(self, f"_parse_{source.file_type}", None)
        sections = parser(source) if callable(parser) else self._parse_text(source)
        return ParsedDocument(doc_id=doc_id, source=source, title=source.metadata.get("title"), sections=tuple(sections))

    def _parse_text(self, source: SourceDocument) -> list[dict[str, object]]:
        sections = []
        for index, block in enumerate([part.strip() for part in source.content.split("\n\n") if part.strip()]):
            sections.append({"heading": None, "text": block, "locator": {"paragraph_index": index}})
        return sections

    def _parse_md(self, source: SourceDocument) -> list[dict[str, object]]:
        sections: list[dict[str, object]] = []
        heading_stack: list[str] = []
        paragraph_index = 0
        buffer: list[str] = []

        def flush() -> None:
            nonlocal paragraph_index
            text = "\n".join(part for part in buffer if part.strip()).strip()
            if not text:
                return
            sections.append(
                {
                    "heading": " / ".join(heading_stack) if heading_stack else None,
                    "text": text,
                    "locator": {
                        "heading_path": list(heading_stack),
                        "paragraph_index": paragraph_index,
                    },
                }
            )
            paragraph_index += 1

        for raw_line in source.content.splitlines():
            line = raw_line.rstrip()
            heading_match = re.match(r"^(#{1,6})\s+(.*)$", line)
            if heading_match:
                flush()
                buffer = []
                level = len(heading_match.group(1))
                title = heading_match.group(2).strip()
                while len(heading_stack) >= level:
                    heading_stack.pop()
                heading_stack.append(title)
                continue
            if not line.strip():
                flush()
                buffer = []
                continue
            buffer.append(line)
        flush()
        return sections or self._parse_text(source)

    def _parse_html(self, source: SourceDocument) -> list[dict[str, object]]:
        pseudo_markdown = source.content.replace("#H1 ", "# ").replace("#H2 ", "## ").replace("#H3 ", "### ")
        pseudo_markdown = pseudo_markdown.replace("#H4 ", "#### ").replace("#H5 ", "##### ").replace("#H6 ", "###### ")
        return self._parse_md(SourceDocument(**{**source.to_dict(), "content": pseudo_markdown}))

    def _parse_json(self, source: SourceDocument) -> list[dict[str, object]]:
        try:
            payload = json.loads(source.content)
        except json.JSONDecodeError:
            return self._parse_text(source)
        sections: list[dict[str, object]] = []
        if isinstance(payload, list):
            for index, item in enumerate(payload):
                sections.append(
                    {
                        "heading": f"record_{index}",
                        "text": json.dumps(item, ensure_ascii=False),
                        "locator": {"record_index": index},
                    }
                )
            return sections
        if isinstance(payload, dict):
            for index, (key, value) in enumerate(payload.items()):
                sections.append(
                    {
                        "heading": key,
                        "text": json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else str(value),
                        "locator": {"field": key, "field_index": index},
                    }
                )
            return sections
        return self._parse_text(source)

    def _parse_pdf(self, source: SourceDocument) -> list[dict[str, object]]:
        pages = [page.strip() for page in re.split(r"\f+", source.content) if page.strip()]
        if not pages:
            return self._parse_text(source)
        sections: list[dict[str, object]] = []
        for page_index, page in enumerate(pages, start=1):
            blocks = [block.strip() for block in page.split("\n\n") if block.strip()]
            for block_index, block in enumerate(blocks):
                sections.append(
                    {
                        "heading": f"page_{page_index}",
                        "text": block,
                        "locator": {"page_no": page_index, "block_index": block_index},
                    }
                )
        return sections

    def _parse_docx(self, source: SourceDocument) -> list[dict[str, object]]:
        return self._parse_md(source)

    def _parse_xlsx(self, source: SourceDocument) -> list[dict[str, object]]:
        return self._parse_excel_like(source)

    def _parse_xls(self, source: SourceDocument) -> list[dict[str, object]]:
        return self._parse_excel_like(source)

    def _parse_excel_like(self, source: SourceDocument) -> list[dict[str, object]]:
        try:
            payload = json.loads(source.content)
        except json.JSONDecodeError:
            return self._parse_text(source)
        sections: list[dict[str, object]] = []
        sheets = payload.get("sheets", []) if isinstance(payload, dict) else []
        for sheet_index, sheet in enumerate(sheets):
            if not isinstance(sheet, dict):
                continue
            headers = ", ".join(str(item) for item in sheet.get("headers", []) if str(item).strip())
            preview_rows = sheet.get("preview_rows", [])
            text_parts = [f"sheet={sheet.get('sheet_name', '')}", f"headers={headers}", f"row_count={sheet.get('row_count', 0)}"]
            if preview_rows:
                text_parts.append(f"preview={json.dumps(preview_rows, ensure_ascii=False)}")
            sections.append(
                {
                    "heading": str(sheet.get("sheet_name") or f"sheet_{sheet_index}"),
                    "text": "\n".join(text_parts),
                    "locator": {
                        "sheet_name": str(sheet.get("sheet_name") or f"sheet_{sheet_index}"),
                        "sheet_index": sheet_index,
                        "row_group_start": 1,
                        "row_group_end": int(sheet.get("row_count") or 0),
                    },
                    "structured_only": True,
                }
            )
        return sections or self._parse_text(source)
