from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterator

from .courtlistener import first_text, safe_filename


@dataclass(frozen=True)
class ExportSummary:
    input_path: Path
    output_dir: Path
    read: int
    written: int
    skipped_invalid: int
    category_counts: dict[str, int]
    manifest_path: Path


def iter_jsonl_rows(path: Path) -> Iterator[dict[str, Any] | None]:
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                yield None
                continue
            yield payload if isinstance(payload, dict) else None


def markdown_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def format_document_markdown(row: dict[str, Any]) -> str:
    title = first_text(row.get("title"), row.get("source_id"), "Untitled legal document")
    metadata = {
        "source": first_text(row.get("source")),
        "source_id": first_text(row.get("source_id")),
        "source_url": first_text(row.get("source_url")),
        "category": first_text(row.get("category"), "general_regulatory"),
        "date_filed": first_text(row.get("date_filed")),
        "docket_number": first_text(row.get("docket_number")),
        "content_sha256": first_text(row.get("content_sha256")),
        "collected_at": first_text(row.get("collected_at")),
    }

    lines = ["---"]
    for key, value in metadata.items():
        lines.append(f'{key}: "{markdown_escape(value)}"')
    lines.extend(["---", "", f"# {title}", "", first_text(row.get("content"))])
    return "\n".join(lines).rstrip() + "\n"


def document_filename(row: dict[str, Any], index: int) -> str:
    source_id = first_text(row.get("source_id"), f"document-{index}")
    return f"{index:05d}_{safe_filename(source_id)}.md"


def export_jsonl_to_category_folders(input_path: Path, output_dir: Path) -> ExportSummary:
    output_dir.mkdir(parents=True, exist_ok=True)

    read = 0
    written = 0
    skipped_invalid = 0
    category_counts: dict[str, int] = {}

    for row in iter_jsonl_rows(input_path):
        if row is None:
            skipped_invalid += 1
            continue

        read += 1
        category = first_text(row.get("category"), "general_regulatory")
        category_dir = output_dir / safe_filename(category)
        category_dir.mkdir(parents=True, exist_ok=True)

        path = category_dir / document_filename(row, read)
        path.write_text(format_document_markdown(row), encoding="utf-8")

        written += 1
        category_counts[category] = category_counts.get(category, 0) + 1

    manifest_path = output_dir / "manifest.json"
    manifest = {
        "generated_at": datetime.now(UTC).isoformat(),
        "input_path": str(input_path),
        "output_dir": str(output_dir),
        "read": read,
        "written": written,
        "skipped_invalid": skipped_invalid,
        "categories": {
            category: {
                "count": count,
                "path": str(output_dir / safe_filename(category)),
            }
            for category, count in sorted(category_counts.items())
        },
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    return ExportSummary(
        input_path=input_path,
        output_dir=output_dir,
        read=read,
        written=written,
        skipped_invalid=skipped_invalid,
        category_counts=category_counts,
        manifest_path=manifest_path,
    )
