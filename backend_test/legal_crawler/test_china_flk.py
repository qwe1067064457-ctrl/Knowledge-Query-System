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

from legal_crawler.china_flk import (
    FlkCategorySpec,
    FlkCrawlConfig,
    crawl_china_flk,
    safe_cn_filename,
    with_limit_per_category,
)


TEST_TMP_ROOT = Path(__file__).resolve().parent / ".test_tmp"


@pytest.fixture
def workspace() -> Path:
    path = TEST_TMP_ROOT / f"case_{uuid.uuid4().hex}"
    path.mkdir(parents=True, exist_ok=False)
    return path


class FakeFlkApi:
    def __init__(self) -> None:
        self.downloaded_urls: list[str] = []

    def search(self, code_ids: tuple[int, ...], page_num: int, page_size: int) -> dict[str, Any]:
        if page_num > 1:
            return {"code": 200, "total": 1, "rows": []}
        return {
            "code": 200,
            "total": 1,
            "rows": [
                {
                    "bbbs": "doc123456",
                    "title": "中华人民共和国示例法",
                    "gbrq": "2026-05-01",
                    "sxrq": "2026-06-01",
                    "flxz": "法律",
                    "zdjgName": "全国人民代表大会常务委员会",
                }
            ],
        }

    def details(self, bbbs: str) -> dict[str, Any]:
        return {
            "bbbs": bbbs,
            "title": "中华人民共和国示例法",
            "flxz": "法律",
            "zdjgName": "全国人民代表大会常务委员会",
            "gbrq": "2026-05-01",
            "sxrq": "2026-06-01",
            "ossFile": {
                "ossWordPath": "prod/example.docx",
                "ossPdfPath": "prod/example.pdf",
            },
            "xgzl": [
                {
                    "fileId": "rel123",
                    "title": "关于示例法草案的说明",
                    "fileType": "docx",
                }
            ],
        }

    def related_details(self, bbbs: str, file_id: str) -> dict[str, Any]:
        return {
            "fileId": file_id,
            "title": "关于示例法草案的说明",
            "ossFilePath": "prod/related.docx",
        }

    def download_info(self, bbbs: str, fmt: str, file_id: str | None = None) -> dict[str, Any] | None:
        suffix = "related.docx" if file_id else f"primary.{fmt}"
        return {
            "url": f"https://example.test/{suffix}?response-content-disposition=attachment;filename=\"{suffix}\""
        }

    def download_bytes(self, url: str) -> bytes:
        self.downloaded_urls.append(url)
        return f"content from {url}".encode("utf-8")


class DetailsFailingFakeFlkApi(FakeFlkApi):
    def details(self, bbbs: str) -> dict[str, Any]:
        raise RuntimeError("details endpoint requires javascript")


def test_safe_cn_filename_preserves_chinese_text() -> None:
    assert safe_cn_filename("中华人民共和国示例法?.docx") == "中华人民共和国示例法_.docx"


def test_crawl_china_flk_writes_primary_pdf_docx_and_related_doc(workspace: Path) -> None:
    output_root = workspace / "cn" / "flk"
    api = FakeFlkApi()
    config = FlkCrawlConfig(
        output_root=output_root,
        sleep_seconds=0,
        related_limit=1,
        category_specs=[
            FlkCategorySpec(
                key="laws",
                label="法律",
                path_parts=("laws",),
                code_ids=(110,),
                limit=1,
            )
        ],
    )

    summary = crawl_china_flk(config, api=api)

    assert summary.records_seen == 1
    assert summary.records_written == 1
    assert summary.assets_downloaded == 3
    assert summary.related_downloaded == 1
    assert summary.skipped_errors == 0
    assert summary.asset_counts == {"docx": 1, "pdf": 1, "related_docx": 1}
    record_dirs = list((output_root / "laws").iterdir())
    assert len(record_dirs) == 1
    assert (record_dirs[0] / "metadata.json").exists()
    assert (record_dirs[0] / "record.md").exists()
    assert (record_dirs[0] / "files" / "primary.docx").exists()
    assert (record_dirs[0] / "files" / "primary.pdf").exists()
    assert (record_dirs[0] / "related" / "related.docx").exists()


def test_crawl_china_flk_keeps_downloading_when_details_are_unavailable(workspace: Path) -> None:
    output_root = workspace / "cn" / "flk"
    config = FlkCrawlConfig(
        output_root=output_root,
        sleep_seconds=0,
        download_related=False,
        category_specs=[
            FlkCategorySpec(
                key="laws",
                label="laws",
                path_parts=("laws",),
                code_ids=(110,),
                limit=1,
            )
        ],
    )

    summary = crawl_china_flk(config, api=DetailsFailingFakeFlkApi())

    assert summary.records_seen == 1
    assert summary.records_written == 1
    assert summary.assets_downloaded == 2
    assert summary.detail_fallbacks == 1
    assert summary.skipped_errors == 0
    manifest = json.loads(summary.manifest_path.read_text(encoding="utf-8"))
    assert manifest["detail_fallbacks"] == 1
    record_dir = next((output_root / "laws").iterdir())
    metadata = json.loads((record_dir / "metadata.json").read_text(encoding="utf-8"))
    assert metadata["detail"] == {}
    assert "RuntimeError" in metadata["detail_fetch_error"]
    assert (record_dir / "files" / "primary.docx").exists()
    assert (record_dir / "files" / "primary.pdf").exists()


def test_crawl_china_flk_writes_manifest_and_cn_index(workspace: Path) -> None:
    output_root = workspace / "cn" / "flk"
    config = FlkCrawlConfig(
        output_root=output_root,
        sleep_seconds=0,
        download_related=False,
        category_specs=[
            FlkCategorySpec(
                key="laws",
                label="法律",
                path_parts=("laws",),
                code_ids=(110,),
                limit=1,
            )
        ],
    )

    summary = crawl_china_flk(config, api=FakeFlkApi())

    manifest = json.loads(summary.manifest_path.read_text(encoding="utf-8"))
    assert manifest["source"]["name"] == "国家法律法规数据库"
    assert manifest["category_counts"]["laws"] == 1
    assert (output_root / "index.md").exists()
    assert (output_root.parent / "index.md").exists()


def test_with_limit_per_category_overrides_all_specs(workspace: Path) -> None:
    config = with_limit_per_category(FlkCrawlConfig(output_root=workspace), 2)

    assert all(spec.limit == 2 for spec in config.category_specs)
