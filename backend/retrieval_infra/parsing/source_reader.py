from __future__ import annotations

import html
import json
import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree


_HTML_TAG_PATTERN = re.compile(r"<[^>]+>")
_HTML_HEADING_PATTERN = re.compile(r"<h([1-6])[^>]*>(.*?)</h\1>", re.IGNORECASE | re.DOTALL)
_HTML_BLOCK_PATTERN = re.compile(r"</?(p|div|section|article|li|br|tr|table|ul|ol)[^>]*>", re.IGNORECASE)
_JSON_JOIN_KEYS = ("question", "answer", "label", "title", "content", "summary", "text", "url")


class SourceReader:
    def read_file_content(self, path: Path) -> str:
        suffix = path.suffix.lower()
        if suffix in {".md", ".txt"}:
            return path.read_text(encoding="utf-8", errors="ignore")
        if suffix == ".json":
            return self._read_json(path)
        if suffix in {".html", ".htm"}:
            raw = path.read_text(encoding="utf-8", errors="ignore")
            raw = _HTML_HEADING_PATTERN.sub(lambda item: f"\n#H{item.group(1)} {html.unescape(_HTML_TAG_PATTERN.sub(' ', item.group(2))).strip()}\n", raw)
            raw = _HTML_BLOCK_PATTERN.sub("\n", raw)
            return html.unescape(_HTML_TAG_PATTERN.sub(" ", raw))
        if suffix == ".pdf":
            return self._read_pdf(path)
        if suffix in {".xlsx", ".xls"}:
            return self._read_excel(path)
        if suffix == ".docx":
            return self._read_docx(path)
        return ""

    def _read_pdf(self, path: Path) -> str:
        try:
            from pypdf import PdfReader
        except Exception:
            txt_sibling = path.with_suffix(".txt")
            return txt_sibling.read_text(encoding="utf-8", errors="ignore") if txt_sibling.exists() else ""
        try:
            reader = PdfReader(str(path))
        except Exception:
            txt_sibling = path.with_suffix(".txt")
            return txt_sibling.read_text(encoding="utf-8", errors="ignore") if txt_sibling.exists() else ""
        pages: list[str] = []
        for page in reader.pages:
            try:
                text = page.extract_text() or ""
            except Exception:
                text = ""
            if text.strip():
                pages.append(text.strip())
        if pages:
            return "\f".join(pages)
        txt_sibling = path.with_suffix(".txt")
        return txt_sibling.read_text(encoding="utf-8", errors="ignore") if txt_sibling.exists() else ""

    def _read_json(self, path: Path) -> str:
        try:
            payload = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
        except json.JSONDecodeError:
            return ""
        return json.dumps(payload, ensure_ascii=False, indent=2)

    def _read_excel(self, path: Path) -> str:
        try:
            with zipfile.ZipFile(path) as archive:
                workbook_root = ElementTree.fromstring(archive.read("xl/workbook.xml"))
                rels_root = ElementTree.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
                shared_strings = self._read_xlsx_shared_strings(archive)
                relationships = {
                    rel.attrib.get("Id", ""): rel.attrib.get("Target", "")
                    for rel in rels_root
                }
                ns = {
                    "main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
                    "rel": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
                }
                sheets_payload: list[dict[str, object]] = []
                for sheet_index, sheet in enumerate(workbook_root.findall(".//main:sheets/main:sheet", ns)):
                    sheet_name = sheet.attrib.get("name", f"sheet_{sheet_index}")
                    rel_id = sheet.attrib.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id", "")
                    target = relationships.get(rel_id, "")
                    if not target:
                        continue
                    normalized_target = target if target.startswith("xl/") else f"xl/{target.lstrip('./')}"
                    rows = self._read_xlsx_rows(archive, normalized_target, shared_strings)
                    headers = rows[0] if rows else []
                    preview = rows[1:4] if len(rows) > 1 else []
                    field_roles = self._infer_field_roles(headers)
                    summary = self._build_sheet_summary(sheet_name, headers, field_roles, len(rows))
                    sheets_payload.append(
                        {
                            "sheet_name": sheet_name,
                            "headers": headers,
                            "row_count": max(0, len(rows) - 1 if headers else len(rows)),
                            "preview_rows": preview,
                            "field_roles": field_roles,
                            "summary": summary,
                        }
                    )
        except Exception:
            return ""
        payload: dict[str, object] = {"type": "excel_workbook", "file": path.name, "sheets": sheets_payload}
        return json.dumps(payload, ensure_ascii=False, indent=2)

    def _infer_field_roles(self, headers: list[str]) -> dict[str, str]:
        roles: dict[str, str] = {}
        for header in headers:
            normalized = str(header).strip().lower()
            if not normalized:
                continue
            if any(token in normalized for token in ("date", "time", "month", "year", "日期", "时间", "月份", "年度")):
                roles[header] = "time"
            elif any(token in normalized for token in ("amount", "price", "revenue", "cost", "sales", "metric", "金额", "价格", "销售", "收入", "成本")):
                roles[header] = "metric"
            elif any(token in normalized for token in ("id", "编号", "编码", "patient", "user", "客户", "订单")):
                roles[header] = "identifier"
            else:
                roles[header] = "category"
        return roles

    def _build_sheet_summary(self, sheet_name: str, headers: list[str], field_roles: dict[str, str], row_count: int) -> str:
        header_text = ", ".join(str(item) for item in headers if str(item).strip())
        role_text = ", ".join(f"{key}:{value}" for key, value in field_roles.items())
        return (
            f"Sheet {sheet_name}. "
            f"Fields: {header_text or 'none'}. "
            f"Field roles: {role_text or 'none'}. "
            f"Approx row count: {max(0, row_count - 1 if headers else row_count)}."
        )

    def _read_docx(self, path: Path) -> str:
        try:
            with zipfile.ZipFile(path) as archive:
                xml_bytes = archive.read("word/document.xml")
        except Exception:
            return ""
        ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
        tree = ElementTree.fromstring(xml_bytes)
        body = tree.find("w:body", ns)
        if body is None:
            return ""
        blocks: list[str] = []
        for child in list(body):
            tag = child.tag.rsplit("}", 1)[-1]
            if tag == "p":
                text = "".join(node.text or "" for node in child.findall(".//w:t", ns)).strip()
                if not text:
                    continue
                style = child.find("w:pPr/w:pStyle", ns)
                style_val = style.attrib.get(f"{{{ns['w']}}}val", "") if style is not None else ""
                heading_match = re.match(r"Heading([1-6])", style_val or "", re.IGNORECASE)
                if heading_match:
                    blocks.append(f"{'#' * int(heading_match.group(1))} {text}")
                else:
                    blocks.append(text)
                continue
            if tag == "tbl":
                rows: list[str] = []
                for row in child.findall(".//w:tr", ns):
                    cells = ["".join(node.text or "" for node in cell.findall(".//w:t", ns)).strip() for cell in row.findall("w:tc", ns)]
                    cleaned = [cell for cell in cells if cell]
                    if cleaned:
                        rows.append(" | ".join(cleaned))
                if rows:
                    blocks.append("\n".join(rows))
        return "\n\n".join(blocks)

    def _read_xlsx_shared_strings(self, archive: zipfile.ZipFile) -> list[str]:
        try:
            root = ElementTree.fromstring(archive.read("xl/sharedStrings.xml"))
        except Exception:
            return []
        ns = {"main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
        values: list[str] = []
        for item in root.findall(".//main:si", ns):
            text = "".join(node.text or "" for node in item.findall(".//main:t", ns)).strip()
            values.append(text)
        return values

    def _read_xlsx_rows(self, archive: zipfile.ZipFile, sheet_path: str, shared_strings: list[str]) -> list[list[str]]:
        try:
            root = ElementTree.fromstring(archive.read(sheet_path))
        except Exception:
            return []
        ns = {"main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
        rows: list[list[str]] = []
        for row in root.findall(".//main:sheetData/main:row", ns):
            values: list[str] = []
            for cell in row.findall("main:c", ns):
                cell_type = cell.attrib.get("t", "")
                value_node = cell.find("main:v", ns)
                inline_node = cell.find("main:is/main:t", ns)
                raw_value = (value_node.text or "").strip() if value_node is not None and value_node.text else ""
                if inline_node is not None and inline_node.text:
                    raw_value = inline_node.text.strip()
                if cell_type == "s" and raw_value.isdigit():
                    index = int(raw_value)
                    raw_value = shared_strings[index] if 0 <= index < len(shared_strings) else raw_value
                if raw_value:
                    values.append(raw_value)
            if values:
                rows.append(values)
        return rows
