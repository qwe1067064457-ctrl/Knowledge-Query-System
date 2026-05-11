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

from legal_crawler.china_civillaw import (
    CivilLawConfig,
    crawl_civillaw_articles,
    extract_title,
    extract_year,
    parse_list_links,
)


TEST_TMP_ROOT = Path(__file__).resolve().parent / ".test_tmp"


@pytest.fixture
def workspace() -> Path:
    path = TEST_TMP_ROOT / f"case_{uuid.uuid4().hex}"
    path.mkdir(parents=True, exist_ok=False)
    return path


class FakeCivilLawApi:
    def __init__(self) -> None:
        self.pages = {
            "https://example.test/list": """
                <html><body>
                  <a href="/lw/t/?id=1">文章一</a>
                  <a href="/lw/t/?id=2">文章二</a>
                </body></html>
            """,
            "https://example.test/lw/t/?id=1": """
                <html><head><title>民商法文章一</title></head>
                <body>发布时间：2024-03-15 正文</body></html>
            """,
            "https://example.test/lw/t/?id=2": """
                <html><head><title>旧文章</title></head>
                <body>发布时间：2021-01-01 正文</body></html>
            """,
        }

    def get_text(self, url: str) -> str:
        return self.pages[url]


def test_parse_list_links_extracts_article_urls() -> None:
    html = '<a href="/lw/t/?id=1">A</a><a href="/gg/?id=2">B</a>'
    assert parse_list_links(html, "https://example.test/list") == ["https://example.test/lw/t/?id=1"]


def test_extract_year_and_title() -> None:
    html = "<html><head><title>示例标题</title></head><body>发布时间：2024-03-15</body></html>"
    assert extract_year(html) == 2024
    assert extract_title(html) == "示例标题"


def test_crawl_civillaw_articles_keeps_2022_plus_raw_html(workspace: Path) -> None:
    output_root = workspace / "cn" / "civillaw"
    summary = crawl_civillaw_articles(
        CivilLawConfig(
            output_root=output_root,
            list_urls=["https://example.test/list"],
            min_year=2022,
            max_records=10,
            sleep_seconds=0,
        ),
        api=FakeCivilLawApi(),
    )

    assert summary.articles_seen == 2
    assert summary.articles_written == 1
    assert summary.skipped_year == 1
    record_dirs = [path for path in output_root.iterdir() if path.is_dir()]
    assert len(record_dirs) == 1
    record_dir = record_dirs[0]
    assert (record_dir / "source.html").exists()
    metadata = json.loads((record_dir / "metadata.json").read_text(encoding="utf-8"))
    assert metadata["year"] == 2024
