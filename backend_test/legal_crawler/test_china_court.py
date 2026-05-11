from __future__ import annotations

import json
import sys
import uuid
from pathlib import Path
from typing import Any

import pytest


ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from legal_crawler.china_court import COURT_BASE_URL, GUIDING_CASE_LIST_URL, CourtGuidingCaseConfig, crawl_court_guiding_cases


TEST_TMP_ROOT = Path(__file__).resolve().parent / ".test_tmp"


@pytest.fixture
def workspace() -> Path:
    path = TEST_TMP_ROOT / f"case_{uuid.uuid4().hex}"
    path.mkdir(parents=True, exist_ok=False)
    return path


GUIDING_CASE_URL = f"{COURT_BASE_URL}/fabu/xiangqing/384771.html"


class FakeCourtApi:
    def __init__(self, *, broken_article: bool = False) -> None:
        self.broken_article = broken_article

    def get_text(self, url: str) -> str:
        if url == GUIDING_CASE_LIST_URL:
            return f"""
            <html>
              <body>
                <a href="/fabu/xiangqing/384771.html">指导性案例199号：高哲宇与深圳市云丝路创新发展基金企业、李斌申请撤销仲裁裁决案</a>
                <a href="/other/ignore.html">普通新闻</a>
              </body>
            </html>
            """
        if url == GUIDING_CASE_URL:
            if self.broken_article:
                raise RuntimeError("article unavailable")
            return """
            <html>
              <body>
                <div class="title">指导性案例199号：高哲宇与深圳市云丝路创新发展基金企业、李斌申请撤销仲裁裁决案</div>
                <div class="detail">指导性案例199号：高哲宇与深圳市云丝路创新发展基金企业、李斌申请撤销仲裁裁决案 来源：最高人民法院 发布时间：2022-12-30 10:13:42 字号：小大 打印本页</div>
                <div class="txt">第一段

第二段</div>
              </body>
            </html>
            """
        raise RuntimeError(f"unexpected url: {url}")


def test_crawl_court_guiding_cases_writes_original_html(workspace: Path) -> None:
    output_root = workspace / "cn" / "guiding_cases"
    summary = crawl_court_guiding_cases(
        CourtGuidingCaseConfig(output_root=output_root, pages=1, sleep_seconds=0),
        api=FakeCourtApi(),
    )

    assert summary.records_seen == 1
    assert summary.records_written == 1
    assert summary.skipped_errors == 0
    record_dirs = [path for path in output_root.iterdir() if path.is_dir()]
    assert len(record_dirs) == 1
    record_dir = record_dirs[0]
    assert (record_dir / "metadata.json").exists()
    assert (record_dir / "source.html").exists()
    assert (record_dir / "case.md").exists()
    metadata = json.loads((record_dir / "metadata.json").read_text(encoding="utf-8"))
    assert metadata["source_url"] == GUIDING_CASE_URL
    assert "指导性案例199号" in (record_dir / "source.html").read_text(encoding="utf-8")


def test_crawl_court_guiding_cases_skips_broken_article_pages(workspace: Path) -> None:
    output_root = workspace / "cn" / "guiding_cases"
    summary = crawl_court_guiding_cases(
        CourtGuidingCaseConfig(output_root=output_root, pages=1, sleep_seconds=0),
        api=FakeCourtApi(broken_article=True),
    )

    assert summary.records_seen == 1
    assert summary.records_written == 0
    assert summary.skipped_errors == 1
    assert json.loads(summary.manifest_path.read_text(encoding="utf-8"))["records_written"] == 0
