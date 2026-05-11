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

from medical_crawler.nature_medicine import (
    NatureMedicineConfig,
    crawl_nature_medicine,
    parse_archive_article_urls,
    parse_article_page,
)


TEST_TMP_ROOT = Path(__file__).resolve().parent / ".test_tmp"


@pytest.fixture
def workspace() -> Path:
    path = TEST_TMP_ROOT / f"case_{uuid.uuid4().hex}"
    path.mkdir(parents=True, exist_ok=False)
    return path


class FakeNatureApi:
    def __init__(self) -> None:
        self.pdf_bytes = b"%PDF-1.4 fake"

    def get_text(self, url: str) -> str:
        if url == "https://www.nature.com/nm/articles?sort=PubDate&year=2026&page=1":
            return """
            <html><body>
              <a href="/articles/s41591-026-04338-1">Article One</a>
              <a href="/articles/s41591-026-04343-4">Article Two</a>
            </body></html>
            """
        if url == "https://www.nature.com/articles/s41591-026-04338-1":
            return """
            <html><head>
              <meta name="citation_title" content="Article One"/>
              <meta name="dc.date" content="2026-05-07"/>
              <meta name="citation_pdf_url" content="https://www.nature.com/articles/s41591-026-04338-1.pdf"/>
              <meta name="citation_doi" content="10.1038/s41591-026-04338-1"/>
            </head><body>Body one</body></html>
            """
        if url == "https://www.nature.com/articles/s41591-026-04343-4":
            return """
            <html><head>
              <meta name="citation_title" content="Article Two"/>
              <meta name="dc.date" content="2021-05-07"/>
              <meta name="citation_pdf_url" content="https://www.nature.com/articles/s41591-026-04343-4.pdf"/>
              <meta name="citation_doi" content="10.1038/s41591-026-04343-4"/>
            </head><body>Body two</body></html>
            """
        raise RuntimeError(f"unexpected url: {url}")

    def get_bytes(self, url: str) -> bytes:
        if url.endswith(".pdf"):
            return self.pdf_bytes
        raise RuntimeError(f"unexpected bytes url: {url}")


def test_parse_archive_article_urls_extracts_nature_links() -> None:
    html = '<a href="/articles/s41591-026-04338-1">A</a><a href="/about">B</a>'
    assert parse_archive_article_urls(html) == ["https://www.nature.com/articles/s41591-026-04338-1"]


def test_parse_article_page_reads_pdf_and_year() -> None:
    html = """
    <html><head>
      <meta name="citation_title" content="Sample"/>
      <meta name="dc.date" content="2026-05-07"/>
      <meta name="citation_pdf_url" content="https://www.nature.com/articles/sample.pdf"/>
      <meta name="citation_doi" content="10.1038/sample"/>
    </head></html>
    """
    article = parse_article_page(html, "https://www.nature.com/articles/sample")
    assert article["title"] == "Sample"
    assert article["year"] == 2026
    assert article["pdf_url"] == "https://www.nature.com/articles/sample.pdf"


def test_crawl_nature_medicine_writes_html_and_pdf(workspace: Path) -> None:
    output_root = workspace / "medicine" / "documents" / "nature_medicine"
    summary = crawl_nature_medicine(
        NatureMedicineConfig(
            output_root=output_root,
            min_year=2022,
            max_year=2026,
            max_records=10,
            sleep_seconds=0,
        ),
        api=FakeNatureApi(),
    )

    assert summary.articles_seen == 2
    assert summary.articles_written == 1
    assert summary.pdf_downloaded == 1
    assert summary.pdf_skipped == 0
    record_dirs = [path for path in output_root.iterdir() if path.is_dir()]
    assert len(record_dirs) == 1
    record_dir = record_dirs[0]
    assert (record_dir / "metadata.json").exists()
    assert (record_dir / "source.html").exists()
    assert (record_dir / "source.pdf").exists()
    metadata = json.loads((record_dir / "metadata.json").read_text(encoding="utf-8"))
    assert metadata["year"] == 2026
