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

from medical_crawler.pmc_ftp_pdf import (
    PmcFtpPdfConfig,
    crawl_pmc_ftp_pdfs,
    extract_year_from_citation,
    parse_csv_rows,
)


TEST_TMP_ROOT = Path(__file__).resolve().parent / ".test_tmp"


@pytest.fixture
def workspace() -> Path:
    path = TEST_TMP_ROOT / f"case_{uuid.uuid4().hex}"
    path.mkdir(parents=True, exist_ok=False)
    return path


class FakePmcApi:
    def iter_csv_rows(self, url: str, *, row_limit: int) -> list[dict[str, str]]:
        if url == "https://example.test/oa.csv":
            rows = [
                {
                    "File": "oa_pdf/ab/cd/article-one.pdf",
                    "Article Citation": "Sample Journal. 2024; 10(1):1-10",
                    "Accession ID": "PMC111",
                    "Last Updated (YYYY-MM-DD HH:MM:SS)": "2024-07-17 10:18:05",
                    "PMID": "123",
                    "License": "CC BY-NC",
                },
                {
                    "File": "oa_pdf/ef/gh/article-two.pdf",
                    "Article Citation": "Old Journal. 2021; 2(1):20-30",
                    "Accession ID": "PMC222",
                    "Last Updated (YYYY-MM-DD HH:MM:SS)": "2024-07-17 10:18:05",
                    "PMID": "456",
                    "License": "CC BY-NC",
                },
                {
                    "File": "oa_package/x/y/no-pdf.tar.gz",
                    "Article Citation": "Ignored Package",
                    "Accession ID": "PMC333",
                    "Last Updated (YYYY-MM-DD HH:MM:SS)": "2024-07-17 10:18:05",
                    "PMID": "789",
                    "License": "CC BY",
                },
            ]
            return rows[:row_limit]
        raise RuntimeError(f"unexpected csv url: {url}")

    def get_bytes(self, url: str) -> bytes:
        if url.endswith("article-one.pdf"):
            return b"%PDF-1.4 fake"
        if url.endswith("article-two.pdf"):
            return b"not-pdf"
        raise RuntimeError(f"unexpected bytes url: {url}")


def test_extract_year_from_citation_reads_recent_year() -> None:
    assert extract_year_from_citation("Sample Journal. 2024; 10(1):1-10") == 2024


def test_extract_year_from_citation_returns_none_when_missing() -> None:
    assert extract_year_from_citation("Sample Journal. Volume only") is None


def test_parse_csv_rows_keeps_only_pdf_rows() -> None:
    csv_text = """File,Article Citation,Accession ID,Last Updated (YYYY-MM-DD HH:MM:SS),PMID,License
oa_pdf/ab/cd/article-one.pdf,Sample Journal. 2024; 10(1):1-10,PMC111,2024-07-17 10:18:05,123,CC BY-NC
oa_package/x/y/no-pdf.tar.gz,Ignored Package,PMC333,2024-07-17 10:18:05,789,CC BY
"""
    rows = parse_csv_rows(csv_text, ftp_base_url="https://ftp.example/")
    assert len(rows) == 1
    assert rows[0]["pmcid"] == "PMC111"
    assert rows[0]["pdf_url"] == "https://ftp.example/oa_pdf/ab/cd/article-one.pdf"


def test_crawl_pmc_ftp_pdfs_writes_pdf_and_metadata(workspace: Path) -> None:
    output_root = workspace / "medicine" / "documents" / "pmc_ftp_pdf"
    summary = crawl_pmc_ftp_pdfs(
        PmcFtpPdfConfig(
            output_root=output_root,
            csv_url="https://example.test/oa.csv",
            ftp_base_url="https://ftp.example/",
            max_records=2,
            sleep_seconds=0,
        ),
        api=FakePmcApi(),
    )

    assert summary.records_seen == 2
    assert summary.records_written == 1
    assert summary.skipped_invalid == 1
    record_dirs = [path for path in output_root.iterdir() if path.is_dir()]
    assert len(record_dirs) == 1
    record_dir = record_dirs[0]
    assert (record_dir / "source.pdf").exists()
    assert (record_dir / "metadata.json").exists()
    metadata = json.loads((record_dir / "metadata.json").read_text(encoding="utf-8"))
    assert metadata["pmcid"] == "PMC111"
    index_text = (output_root / "index.md").read_text(encoding="utf-8-sig")
    assert "`total_pdf_documents`：1" in index_text
    assert "`records_written_this_run`：1" in index_text
    assert "`skipped_invalid`：1" in index_text
