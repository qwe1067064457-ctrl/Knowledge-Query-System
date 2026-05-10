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

from legal_crawler.ecfr import (
    EcfrConfig,
    EcfrTitle,
    classify_ecfr_section,
    crawl_ecfr_sections,
    iter_sections,
    normalize_ecfr_section,
)


TEST_TMP_ROOT = Path(__file__).resolve().parent / ".test_tmp"


@pytest.fixture
def workspace() -> Path:
    path = TEST_TMP_ROOT / f"case_{uuid.uuid4().hex}"
    path.mkdir(parents=True, exist_ok=False)
    return path


class FakeEcfrClient:
    def __init__(self, xml_by_title: dict[int, str]) -> None:
        self.xml_by_title = xml_by_title

    def fetch_titles(self, config: EcfrConfig) -> list[EcfrTitle]:
        return [
            EcfrTitle(number=1, name="General Provisions", issue_date="2024-05-17"),
            EcfrTitle(number=29, name="Labor", issue_date="2024-05-17"),
        ]

    def fetch_title_xml(self, config: EcfrConfig, title: EcfrTitle) -> str:
        return self.xml_by_title[title.number]


def sample_xml(section_number: str, head: str, body: str) -> str:
    return f"""
    <ECFR>
      <DIV8 N="{section_number}" TYPE="SECTION">
        <HEAD>{head}</HEAD>
        <P>{body}</P>
      </DIV8>
    </ECFR>
    """


def read_jsonl(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_iter_sections_accepts_ecfr_section_divs() -> None:
    sections = list(iter_sections(sample_xml("1.1", "§ 1.1 Definitions.", "A rule.")))

    assert len(sections) == 1
    assert sections[0].attrib["N"] == "1.1"


def test_normalize_ecfr_section_builds_rag_document() -> None:
    title = EcfrTitle(number=29, name="Labor", issue_date="2024-05-17")
    section = next(iter_sections(sample_xml("1910.1", "§ 1910.1 Purpose.", "The employer must comply.")))

    document = normalize_ecfr_section(title, section, collected_at="2026-05-10T00:00:00+00:00")

    assert document is not None
    assert document.source == "ecfr"
    assert document.source_id == "ecfr:title-29:section-1910.1"
    assert document.title == "§ 1910.1 Purpose."
    assert document.category == "employment_labor"
    assert "employer must comply" in document.content


def test_normalize_ecfr_section_rejects_missing_section_number() -> None:
    title = EcfrTitle(number=1, name="General Provisions", issue_date="2024-05-17")
    section = next(iter_sections(sample_xml("", "Missing number", "Text")))

    assert normalize_ecfr_section(title, section) is None


def test_classify_ecfr_section_detects_tax_title() -> None:
    assert classify_ecfr_section("Internal Revenue", "§ 1.1", "General rule.") == "tax"


def test_classify_ecfr_section_falls_back_to_general() -> None:
    assert classify_ecfr_section("Unknown Title", "§ 1.1", "Plain rule text.") == "general_regulatory"


def test_crawl_ecfr_sections_writes_limit_and_category_files(workspace: Path) -> None:
    output = workspace / "ecfr.jsonl"
    client = FakeEcfrClient(
        {
            1: sample_xml("1.1", "§ 1.1 Definitions.", "General provisions text."),
            29: sample_xml("1910.1", "§ 1910.1 Purpose.", "The employer must comply."),
        }
    )

    summary = crawl_ecfr_sections(EcfrConfig(output_path=output, limit=2, sleep_seconds=0), client=client)

    assert summary.titles_fetched == 2
    assert summary.written == 2
    assert [row["source"] for row in read_jsonl(output)] == ["ecfr", "ecfr"]
    assert (workspace / "by_category" / "government_administration.jsonl").exists()
    assert (workspace / "by_category" / "employment_labor.jsonl").exists()
    assert (workspace / "category_manifest.json").exists()


def test_crawl_ecfr_sections_skips_duplicates_on_resume(workspace: Path) -> None:
    output = workspace / "ecfr.jsonl"
    client = FakeEcfrClient(
        {
            1: sample_xml("1.1", "§ 1.1 Definitions.", "General provisions text."),
            29: sample_xml("1.1", "§ 1.1 Definitions.", "General provisions text."),
        }
    )

    summary = crawl_ecfr_sections(EcfrConfig(output_path=output, limit=2, sleep_seconds=0), client=client)

    assert summary.written == 2
    assert summary.skipped_duplicate == 0


def test_ecfr_config_rejects_invalid_limit(workspace: Path) -> None:
    with pytest.raises(ValueError, match="limit"):
        EcfrConfig(output_path=workspace / "out.jsonl", limit=0).normalized()
