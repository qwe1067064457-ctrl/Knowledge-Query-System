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

from medical_crawler.yiigle_cn import (
    YiigleCnConfig,
    crawl_yiigle_cn_articles,
    extract_article_payload,
    parse_home_article_links,
)


TEST_TMP_ROOT = Path(__file__).resolve().parent / ".test_tmp"


@pytest.fixture
def workspace() -> Path:
    path = TEST_TMP_ROOT / f"case_{uuid.uuid4().hex}"
    path.mkdir(parents=True, exist_ok=False)
    return path


FULLTEXT_ARTICLE_HTML = """
<html><head>
  <meta name="citation_title" content="示例文章一"/>
  <meta name="citation_publication_date" content="2024/04/15"/>
  <meta name="citation_author" content="张三"/>
  <meta name="citation_author" content="李四"/>
  <meta name="citation_abstract" content="这是摘要内容。"/>
  <meta name="citation_keyword" content="基层医疗"/>
  <meta name="citation_keyword" content="消化内科"/>
  <meta name="citation_journal_title" content="中国基层医药"/>
  <meta name="citation_doi" content="10.3760/example"/>
</head><body>
<script>
window.__NUXT__={data:[{xmlData:"\\u003C?xml version=\\"1.0\\" encoding=\\"UTF-8\\"?\\u003E\\n\\u003Carticle xmlns:xlink=\\"http:\\u002F\\u002Fwww.w3.org\\u002F1999\\u002Fxlink\\"\\u003E\\n\\u003Cbody\\u003E\\n\\u003Csec\\u003E\\n\\u003Ctitle\\u003E1 方法\\u003C\\u002Ftitle\\u003E\\n\\u003Cp\\u003E方法段落。\\u003C\\u002Fp\\u003E\\n\\u003C\\u002Fsec\\u003E\\n\\u003Csec\\u003E\\n\\u003Ctitle\\u003E2 结果\\u003C\\u002Ftitle\\u003E\\n\\u003Cp\\u003E结果段落。\\u003C\\u002Fp\\u003E\\n\\u003Ctable-wrap\\u003E\\n\\u003Clabel\\u003E表1\\u003C\\u002Flabel\\u003E\\n\\u003Ccaption\\u003E\\u003Cp\\u003E疗效比较。\\u003C\\u002Fp\\u003E\\u003C\\u002Fcaption\\u003E\\n\\u003C\\u002Ftable-wrap\\u003E\\n\\u003C\\u002Fsec\\u003E\\n\\u003C\\u002Fbody\\u003E\\n\\u003Cfront-stub\\u003E\\n\\u003Cself-uri content-type=\\"pdf\\" xlink:href=\\"r\\u002Fcms\\u002Fsample.pdf\\"\\u002F\\u003E\\n\\u003C\\u002Ffront-stub\\u003E\\n\\u003C\\u002Farticle\\u003E"}]};
</script>
</body></html>
"""


ABSTRACT_ONLY_ARTICLE_HTML = """
<html><head>
  <meta name="citation_title" content="旧文章"/>
  <meta name="citation_publication_date" content="2021/04/15"/>
  <meta name="citation_abstract" content="旧摘要。"/>
  <meta name="keywords" content="旧词"/>
  <meta name="citation_journal_title" content="中国基层医药"/>
</head><body>detail</body></html>
"""


class FakeYiigleApi:
    def get_text(self, url: str) -> str:
        if url == "http://example.journal/":
            return """
            <html><body>
              <a href="https://rs.yiigle.com/cmaid/1001">A1</a>
              <a href="https://rs.yiigle.com/cmaid/1002">A2</a>
            </body></html>
            """
        if url == "https://rs.yiigle.com/cmaid/1001":
            return FULLTEXT_ARTICLE_HTML
        if url == "https://rs.yiigle.com/cmaid/1002":
            return ABSTRACT_ONLY_ARTICLE_HTML
        raise RuntimeError(f"unexpected url: {url}")

    def get_binary(self, url: str) -> bytes:
        if url == "https://rs.yiigle.com/r/cms/sample.pdf":
            return b"%PDF-1.7 sample"
        raise RuntimeError(f"unexpected binary url: {url}")


class FakeYiigleApiWithoutPdf(FakeYiigleApi):
    def get_binary(self, url: str) -> bytes:
        raise RuntimeError("pdf blocked")


def test_parse_home_article_links_extracts_cmaid_urls() -> None:
    html = '<a href="https://rs.yiigle.com/cmaid/1001">A</a><a href="/about">B</a>'
    assert parse_home_article_links(html, "http://example.journal/") == ["https://rs.yiigle.com/cmaid/1001"]


def test_extract_article_payload_prefers_fulltext_xml_and_pdf_url() -> None:
    article = extract_article_payload(FULLTEXT_ARTICLE_HTML, "https://rs.yiigle.com/cmaid/1001")
    assert article["title"] == "示例文章一"
    assert article["year"] == 2024
    assert article["body_kind"] == "fulltext_xml"
    assert "方法段落。" in article["body"]
    assert "结果段落。" in article["body"]
    assert "表1 疗效比较。" in article["body"]
    assert article["keywords"] == ["基层医疗", "消化内科"]
    assert article["pdf_url"] == "https://rs.yiigle.com/r/cms/sample.pdf"
    assert article["xml_available"] is True


def test_extract_article_payload_falls_back_to_abstract_when_no_xml() -> None:
    article = extract_article_payload(ABSTRACT_ONLY_ARTICLE_HTML, "https://rs.yiigle.com/cmaid/1002")
    assert article["body_kind"] == "abstract_only"
    assert article["body"] == "旧摘要。"
    assert article["pdf_url"] == ""
    assert article["xml_available"] is False


def test_crawl_yiigle_cn_articles_writes_html_content_and_pdf(workspace: Path) -> None:
    output_root = workspace / "medicine" / "documents" / "yiigle_cn"
    summary = crawl_yiigle_cn_articles(
        YiigleCnConfig(
            output_root=output_root,
            journal_home_url="http://example.journal/",
            min_year=2022,
            max_records=10,
            sleep_seconds=0,
        ),
        api=FakeYiigleApi(),
    )

    assert summary.articles_seen == 2
    assert summary.articles_written == 1
    assert summary.skipped_year == 1
    record_dirs = [path for path in output_root.iterdir() if path.is_dir()]
    assert len(record_dirs) == 1
    record_dir = record_dirs[0]
    assert (record_dir / "source.html").exists()
    assert (record_dir / "content.md").exists()
    assert (record_dir / "source.pdf").exists()
    metadata = json.loads((record_dir / "metadata.json").read_text(encoding="utf-8"))
    assert metadata["year"] == 2024
    content = (record_dir / "content.md").read_text(encoding="utf-8-sig")
    assert "方法段落。" in content
    assert "结果段落。" in content
    index_text = (output_root / "index.md").read_text(encoding="utf-8-sig")
    assert "`fulltext_xml`：1" in index_text
    assert "`pdf_downloaded`：1" in index_text


def test_crawl_yiigle_cn_articles_keeps_record_when_pdf_download_fails(workspace: Path) -> None:
    output_root = workspace / "medicine" / "documents" / "yiigle_cn"
    summary = crawl_yiigle_cn_articles(
        YiigleCnConfig(
            output_root=output_root,
            journal_home_url="http://example.journal/",
            min_year=2022,
            max_records=1,
            sleep_seconds=0,
        ),
        api=FakeYiigleApiWithoutPdf(),
    )

    assert summary.articles_written == 1
    record_dir = next(path for path in output_root.iterdir() if path.is_dir())
    assert (record_dir / "source.html").exists()
    assert (record_dir / "content.md").exists()
    assert not (record_dir / "source.pdf").exists()
