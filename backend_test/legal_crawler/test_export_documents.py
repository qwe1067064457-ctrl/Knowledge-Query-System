from __future__ import annotations

import json
import sys
import uuid
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from legal_crawler.export_documents import export_jsonl_to_category_folders


TEST_TMP_ROOT = Path(__file__).resolve().parent / ".test_tmp"


@pytest.fixture
def workspace() -> Path:
    path = TEST_TMP_ROOT / f"case_{uuid.uuid4().hex}"
    path.mkdir(parents=True, exist_ok=False)
    return path


def write_jsonl(path: Path, rows: list[dict[str, object] | str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    for row in rows:
        lines.append(row if isinstance(row, str) else json.dumps(row, ensure_ascii=False))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_export_jsonl_to_category_folders_writes_one_markdown_file_per_document(workspace: Path) -> None:
    input_path = workspace / "docs.jsonl"
    output_dir = workspace / "out"
    write_jsonl(
        input_path,
        [
            {
                "source": "ecfr",
                "source_id": "ecfr:title-1:section-1.1",
                "source_url": "https://example.test/1",
                "category": "government_administration",
                "title": "§ 1.1 Definitions.",
                "content": "Definitions content.",
            },
            {
                "source": "ecfr",
                "source_id": "ecfr:title-7:section-2.1",
                "category": "agriculture",
                "title": "§ 2.1 Agriculture.",
                "content": "Agriculture content.",
            },
        ],
    )

    summary = export_jsonl_to_category_folders(input_path, output_dir)

    assert summary.read == 2
    assert summary.written == 2
    assert (output_dir / "government_administration" / "00001_ecfr_title-1_section-1_1.md").exists()
    assert (output_dir / "agriculture" / "00002_ecfr_title-7_section-2_1.md").exists()
    assert "Definitions content." in (
        output_dir / "government_administration" / "00001_ecfr_title-1_section-1_1.md"
    ).read_text(encoding="utf-8")


def test_export_jsonl_to_category_folders_skips_invalid_json_lines(workspace: Path) -> None:
    input_path = workspace / "docs.jsonl"
    output_dir = workspace / "out"
    write_jsonl(
        input_path,
        [
            "{bad json",
            {
                "source_id": "doc-1",
                "category": "general_regulatory",
                "title": "Valid",
                "content": "Valid content.",
            },
        ],
    )

    summary = export_jsonl_to_category_folders(input_path, output_dir)

    assert summary.read == 1
    assert summary.written == 1
    assert summary.skipped_invalid == 1
    assert (output_dir / "general_regulatory" / "00001_doc-1.md").exists()
