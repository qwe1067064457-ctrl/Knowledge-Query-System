from __future__ import annotations

import hashlib
import json
import re
import time
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol
from urllib.parse import unquote, urlparse, parse_qs

import httpx

from .courtlistener import first_text, normalize_whitespace


FLK_BASE_URL = "https://flk.npc.gov.cn"


@dataclass(frozen=True)
class FlkCategorySpec:
    key: str
    label: str
    path_parts: tuple[str, ...]
    code_ids: tuple[int, ...]
    limit: int


DEFAULT_CATEGORY_SPECS = [
    FlkCategorySpec(
        key="laws",
        label="法律",
        path_parts=("laws",),
        code_ids=(110, 120, 130, 140, 150, 155, 160, 170),
        limit=60,
    ),
    FlkCategorySpec(
        key="administrative_regulations",
        label="行政法规",
        path_parts=("regulations", "administrative_regulations"),
        code_ids=(210,),
        limit=60,
    ),
    FlkCategorySpec(
        key="supervision_regulations",
        label="监察法规",
        path_parts=("regulations", "supervision_regulations"),
        code_ids=(220,),
        limit=10,
    ),
    FlkCategorySpec(
        key="local_regulations",
        label="地方法规",
        path_parts=("local_regulations",),
        code_ids=(230, 260, 270, 290, 295, 300),
        limit=60,
    ),
    FlkCategorySpec(
        key="judicial_interpretations",
        label="司法解释",
        path_parts=("judicial_interpretations",),
        code_ids=(320, 330, 340),
        limit=60,
    ),
    FlkCategorySpec(
        key="modification_decisions",
        label="修改、废止的决定",
        path_parts=("modification_decisions",),
        code_ids=(200, 215, 310, 350),
        limit=30,
    ),
]


@dataclass(frozen=True)
class FlkCrawlConfig:
    output_root: Path
    page_size: int = 20
    sleep_seconds: float = 0.2
    timeout_seconds: float = 60.0
    download_docx: bool = True
    download_pdf: bool = True
    download_related: bool = True
    fetch_details: bool = True
    related_limit: int = 100
    trust_env: bool = False
    category_specs: list[FlkCategorySpec] = field(default_factory=lambda: list(DEFAULT_CATEGORY_SPECS))

    def normalized(self) -> "FlkCrawlConfig":
        if self.page_size < 1:
            raise ValueError("page_size must be at least 1")
        if self.sleep_seconds < 0:
            raise ValueError("sleep_seconds cannot be negative")
        if self.related_limit < 0:
            raise ValueError("related_limit cannot be negative")
        return FlkCrawlConfig(
            output_root=self.output_root,
            page_size=min(self.page_size, 50),
            sleep_seconds=self.sleep_seconds,
            timeout_seconds=self.timeout_seconds,
            download_docx=self.download_docx,
            download_pdf=self.download_pdf,
            download_related=self.download_related,
            fetch_details=self.fetch_details,
            related_limit=self.related_limit,
            trust_env=self.trust_env,
            category_specs=list(self.category_specs),
        )


@dataclass(frozen=True)
class FlkCrawlSummary:
    output_root: Path
    records_seen: int
    records_written: int
    assets_downloaded: int
    related_downloaded: int
    skipped_existing_assets: int
    skipped_errors: int
    detail_fallbacks: int
    category_counts: dict[str, int]
    asset_counts: dict[str, int]
    manifest_path: Path


class FlkApi(Protocol):
    def search(self, code_ids: tuple[int, ...], page_num: int, page_size: int) -> dict[str, Any]:
        ...

    def details(self, bbbs: str) -> dict[str, Any]:
        ...

    def related_details(self, bbbs: str, file_id: str) -> dict[str, Any]:
        ...

    def download_info(self, bbbs: str, fmt: str, file_id: str | None = None) -> dict[str, Any] | None:
        ...

    def download_bytes(self, url: str) -> bytes:
        ...


class FlkHttpApi:
    def __init__(self, config: FlkCrawlConfig) -> None:
        self.config = config.normalized()
        self.client = httpx.Client(
            timeout=self.config.timeout_seconds,
            follow_redirects=True,
            trust_env=self.config.trust_env,
            headers={
                "Content-Type": "application/json;charset=utf-8",
                "User-Agent": "Skill-First-Hybrid-RAG China legal crawler/1.0",
            },
        )

    def close(self) -> None:
        self.client.close()

    def _json_request(self, method: str, url: str, **kwargs: Any) -> dict[str, Any]:
        last_error: Exception | None = None
        for _ in range(3):
            try:
                response = self.client.request(method, url, **kwargs)
                response.raise_for_status()
                payload = response.json()
                return payload if isinstance(payload, dict) else {}
            except (httpx.HTTPError, json.JSONDecodeError) as exc:
                last_error = exc
                time.sleep(0.5)
        raise RuntimeError(f"FLK request did not return valid JSON: {url}") from last_error

    def search(self, code_ids: tuple[int, ...], page_num: int, page_size: int) -> dict[str, Any]:
        payload = {
            "searchRange": 1,
            "sxrq": [],
            "gbrq": [],
            "searchType": 2,
            "sxx": [],
            "gbrqYear": [],
            "flfgCodeId": list(code_ids),
            "zdjgCodeId": [],
            "searchContent": "",
            "orderByParam": {"order": "-1", "sort": ""},
            "pageNum": page_num,
            "pageSize": page_size,
        }
        return self._json_request("POST", f"{FLK_BASE_URL}/law-search/search/list", json=payload)

    def details(self, bbbs: str) -> dict[str, Any]:
        payload = self._json_request("GET", f"{FLK_BASE_URL}/law-search/search/flfgDetails", params={"bbbs": bbbs})
        return payload.get("data") or {}

    def related_details(self, bbbs: str, file_id: str) -> dict[str, Any]:
        payload = self._json_request(
            "GET",
            f"{FLK_BASE_URL}/law-search/search/xgzlDetails",
            params={"bbbs": bbbs, "fileId": file_id},
        )
        return payload.get("data") or {}

    def download_info(self, bbbs: str, fmt: str, file_id: str | None = None) -> dict[str, Any] | None:
        params = {"bbbs": bbbs, "format": fmt}
        if file_id:
            params["fileId"] = file_id
        payload = self._json_request("GET", f"{FLK_BASE_URL}/law-search/download/pc", params=params)
        data = payload.get("data")
        return data if isinstance(data, dict) else None

    def download_bytes(self, url: str) -> bytes:
        response = self.client.get(url)
        response.raise_for_status()
        return response.content


def safe_cn_filename(value: str, *, fallback: str = "document", max_length: int = 80) -> str:
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]+', "_", value)
    cleaned = re.sub(r"\s+", "_", cleaned).strip("._ ")
    cleaned = cleaned or fallback
    if len(cleaned) <= max_length:
        return cleaned
    suffix = Path(cleaned).suffix
    if suffix and len(suffix) < max_length // 2:
        return f"{Path(cleaned).stem[: max_length - len(suffix)]}{suffix}"
    return cleaned[:max_length]


def file_name_from_download_info(info: dict[str, Any], fallback: str) -> str:
    url = first_text(info.get("url"), info.get("urlIn"))
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    disposition = first_text(query.get("response-content-disposition", [""])[0])
    match = re.search(r'filename="?([^"]+)"?', unquote(disposition))
    if match:
        return safe_cn_filename(match.group(1), fallback=fallback, max_length=56)
    return safe_cn_filename(fallback, fallback=fallback, max_length=56)


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def category_dir(output_root: Path, spec: FlkCategorySpec) -> Path:
    path = output_root
    for part in spec.path_parts:
        path = path / part
    return path


def record_dir(base_dir: Path, row: dict[str, Any]) -> Path:
    title = safe_cn_filename(
        first_text(row.get("title"), row.get("bbbs")),
        fallback=first_text(row.get("bbbs"), "record"),
        max_length=36,
    )
    date = first_text(row.get("gbrq")).replace("-", "")
    prefix = date or "undated"
    return base_dir / f"{prefix}_{first_text(row.get('bbbs'))[:12]}_{title}"


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.rstrip() + "\n", encoding="utf-8")


def render_record_markdown(row: dict[str, Any], detail: dict[str, Any], assets: list[dict[str, Any]]) -> str:
    title = first_text(detail.get("title"), row.get("title"), "未命名法律文献")
    lines = [
        "---",
        f'title: "{title}"',
        f'source: "国家法律法规数据库"',
        f'source_url: "{FLK_BASE_URL}/detail?id={first_text(row.get("bbbs"))}"',
        f'bbbs: "{first_text(row.get("bbbs"))}"',
        f'flxz: "{first_text(detail.get("flxz"), row.get("flxz"))}"',
        f'zdjg_name: "{first_text(detail.get("zdjgName"), row.get("zdjgName"))}"',
        f'gbrq: "{first_text(detail.get("gbrq"), row.get("gbrq"))}"',
        f'sxrq: "{first_text(detail.get("sxrq"), row.get("sxrq"))}"',
        "---",
        "",
        f"# {title}",
        "",
        f"- 来源：国家法律法规数据库",
        f"- 类型：{first_text(detail.get('flxz'), row.get('flxz'))}",
        f"- 制定机关：{first_text(detail.get('zdjgName'), row.get('zdjgName'))}",
        f"- 公布日期：{first_text(detail.get('gbrq'), row.get('gbrq'))}",
        f"- 施行日期：{first_text(detail.get('sxrq'), row.get('sxrq'))}",
        f"- 原始页面：{FLK_BASE_URL}/detail?id={first_text(row.get('bbbs'))}",
        "",
        "## 本地文件",
        "",
    ]
    for asset in assets:
        lines.append(f"- `{asset['relative_path']}` ({asset['kind']}, {asset['bytes']} bytes)")
    if not assets:
        lines.append("- 暂无可下载文件。")
    return "\n".join(lines)


def download_asset(
    *,
    api: FlkApi,
    info: dict[str, Any],
    target_dir: Path,
    fallback_name: str,
    kind: str,
) -> tuple[dict[str, Any], bool]:
    url = first_text(info.get("url"))
    if not url:
        raise ValueError("download info does not include url")

    filename = file_name_from_download_info(info, fallback_name)
    target_path = target_dir / filename
    if target_path.exists():
        return (
            {
                "kind": kind,
                "path": str(target_path),
                "relative_path": target_path.name,
                "bytes": target_path.stat().st_size,
                "sha256": "",
                "url": url,
                "skipped_existing": True,
            },
            False,
        )

    content = api.download_bytes(url)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_bytes(content)
    return (
        {
            "kind": kind,
            "path": str(target_path),
            "relative_path": target_path.name,
            "bytes": len(content),
            "sha256": sha256_bytes(content),
            "url": url,
            "skipped_existing": False,
        },
        True,
    )


def try_download_info(
    api: FlkApi,
    bbbs: str,
    fmt: str,
    *,
    file_id: str | None = None,
) -> tuple[dict[str, Any] | None, bool]:
    try:
        return api.download_info(bbbs, fmt, file_id=file_id), False
    except Exception:
        return None, True


def iter_category_rows(api: FlkApi, spec: FlkCategorySpec, page_size: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    page_num = 1
    while len(rows) < spec.limit:
        payload = api.search(spec.code_ids, page_num=page_num, page_size=page_size)
        page_rows = payload.get("rows") or []
        if not isinstance(page_rows, list) or not page_rows:
            break
        for row in page_rows:
            if isinstance(row, dict):
                rows.append(row)
                if len(rows) >= spec.limit:
                    break
        total = int(payload.get("total") or 0)
        if page_num * page_size >= total:
            break
        page_num += 1
    return rows


def crawl_china_flk(config: FlkCrawlConfig, *, api: FlkApi | None = None) -> FlkCrawlSummary:
    config = config.normalized()
    config.output_root.mkdir(parents=True, exist_ok=True)
    own_api = FlkHttpApi(config) if api is None else None
    flk_api = api or own_api
    assert flk_api is not None

    records_seen = 0
    records_written = 0
    assets_downloaded = 0
    related_downloaded = 0
    skipped_existing_assets = 0
    skipped_errors = 0
    detail_fallbacks = 0
    category_counts: dict[str, int] = {}
    asset_counts: dict[str, int] = {}
    related_remaining = config.related_limit

    try:
        for spec in config.category_specs:
            rows = iter_category_rows(flk_api, spec, config.page_size)
            base_dir = category_dir(config.output_root, spec)
            category_counts[spec.key] = 0

            for row in rows:
                records_seen += 1
                bbbs = first_text(row.get("bbbs"))
                if not bbbs:
                    continue

                detail_fetch_error = ""
                if config.fetch_details:
                    try:
                        detail = flk_api.details(bbbs)
                    except Exception as exc:
                        detail = {}
                        detail_fallbacks += 1
                        detail_fetch_error = f"{type(exc).__name__}: {exc}"
                else:
                    detail = {}
                    detail_fetch_error = "details skipped by configuration"
                target_dir = record_dir(base_dir, row)
                files_dir = target_dir / "files"
                assets: list[dict[str, Any]] = []

                if config.download_docx:
                    info, failed = try_download_info(flk_api, bbbs, "docx")
                    if failed:
                        skipped_errors += 1
                    if info:
                        try:
                            asset, downloaded = download_asset(
                                api=flk_api,
                                info=info,
                                target_dir=files_dir,
                                fallback_name=f"{first_text(row.get('title'))}.docx",
                                kind="primary_docx",
                            )
                        except Exception:
                            skipped_errors += 1
                            asset = None
                            downloaded = False
                        if asset is not None:
                            assets.append(asset)
                            if downloaded:
                                assets_downloaded += 1
                                asset_counts["docx"] = asset_counts.get("docx", 0) + 1
                            else:
                                skipped_existing_assets += 1

                if config.download_pdf:
                    info, failed = try_download_info(flk_api, bbbs, "pdf")
                    if failed:
                        skipped_errors += 1
                    if info:
                        try:
                            asset, downloaded = download_asset(
                                api=flk_api,
                                info=info,
                                target_dir=files_dir,
                                fallback_name=f"{first_text(row.get('title'))}.pdf",
                                kind="primary_pdf",
                            )
                        except Exception:
                            skipped_errors += 1
                            asset = None
                            downloaded = False
                        if asset is not None:
                            assets.append(asset)
                            if downloaded:
                                assets_downloaded += 1
                                asset_counts["pdf"] = asset_counts.get("pdf", 0) + 1
                            else:
                                skipped_existing_assets += 1

                if config.download_related and related_remaining > 0:
                    related_dir = target_dir / "related"
                    for related in detail.get("xgzl") or []:
                        if related_remaining <= 0:
                            break
                        if not isinstance(related, dict):
                            continue
                        file_id = first_text(related.get("fileId"))
                        if not file_id:
                            continue
                        try:
                            related_detail = flk_api.related_details(bbbs, file_id)
                        except Exception:
                            skipped_errors += 1
                            continue
                        info, failed = try_download_info(flk_api, bbbs, "docx", file_id=file_id)
                        if failed:
                            skipped_errors += 1
                            continue
                        if not info:
                            continue
                        fallback = f"{first_text(related_detail.get('title'), related.get('title'), file_id)}.docx"
                        try:
                            asset, downloaded = download_asset(
                                api=flk_api,
                                info=info,
                                target_dir=related_dir,
                                fallback_name=fallback,
                                kind="related_docx",
                            )
                        except Exception:
                            skipped_errors += 1
                            continue
                        asset["title"] = first_text(related_detail.get("title"), related.get("title"))
                        assets.append(asset)
                        if downloaded:
                            assets_downloaded += 1
                            related_downloaded += 1
                            related_remaining -= 1
                            asset_counts["related_docx"] = asset_counts.get("related_docx", 0) + 1
                        else:
                            skipped_existing_assets += 1

                record_payload = {
                    "source": "国家法律法规数据库",
                    "source_url": f"{FLK_BASE_URL}/detail?id={bbbs}",
                    "category_key": spec.key,
                    "category_label": spec.label,
                    "row": row,
                    "detail": detail,
                    "detail_fetch_error": detail_fetch_error,
                    "assets": assets,
                    "collected_at": datetime.now(UTC).isoformat(),
                }
                write_json(target_dir / "metadata.json", record_payload)
                write_text(target_dir / "record.md", render_record_markdown(row, detail, assets))
                records_written += 1
                category_counts[spec.key] = category_counts.get(spec.key, 0) + 1

                if config.sleep_seconds:
                    time.sleep(config.sleep_seconds)
    finally:
        if own_api is not None:
            own_api.close()

    manifest_path = config.output_root / "manifest.json"
    manifest = {
        "generated_at": datetime.now(UTC).isoformat(),
        "source": {
            "name": "国家法律法规数据库",
            "url": FLK_BASE_URL,
            "country": "China",
        },
        "output_root": str(config.output_root),
        "records_seen": records_seen,
        "records_written": records_written,
        "assets_downloaded": assets_downloaded,
        "related_downloaded": related_downloaded,
        "skipped_existing_assets": skipped_existing_assets,
        "skipped_errors": skipped_errors,
        "detail_fallbacks": detail_fallbacks,
        "category_counts": category_counts,
        "asset_counts": asset_counts,
    }
    write_json(manifest_path, manifest)
    write_text(config.output_root / "index.md", render_flk_index(manifest))
    refresh_cn_index(config.output_root.parent)

    return FlkCrawlSummary(
        output_root=config.output_root,
        records_seen=records_seen,
        records_written=records_written,
        assets_downloaded=assets_downloaded,
        related_downloaded=related_downloaded,
        skipped_existing_assets=skipped_existing_assets,
        skipped_errors=skipped_errors,
        detail_fallbacks=detail_fallbacks,
        category_counts=category_counts,
        asset_counts=asset_counts,
        manifest_path=manifest_path,
    )


def render_flk_index(manifest: dict[str, Any]) -> str:
    category_lines = "\n".join(
        f"- `{category}`：{count} 条" for category, count in sorted(manifest.get("category_counts", {}).items())
    )
    asset_lines = "\n".join(
        f"- `{asset_type}`：{count} 个" for asset_type, count in sorted(manifest.get("asset_counts", {}).items())
    )
    return f"""# 国家法律法规数据库资料

来源：国家法律法规数据库

国家/地区：中国

资料类型：法律、行政法规、监察法规、地方法规、司法解释、修改废止决定及相关立法资料。

## 分类数量

{category_lines}

## 已下载文件类型

{asset_lines or "- 暂无附件。"}

## 目录说明

- 每条法律法规记录保存为一个目录。
- `metadata.json` 保存接口元数据和本地附件清单。
- `record.md` 保存人工/agent 可读摘要。
- `files/` 保存正文附件，例如 `.docx`、`.pdf`。
- `related/` 保存相关立法资料附件。
"""


def refresh_cn_index(cn_root: Path) -> None:
    write_text(
        cn_root / "index.md",
        """# 中国法律资料

本目录用于整理中国法律文献，优先使用公开官方来源。

## 已建设来源

- `flk/`：国家法律法规数据库，包含法律、行政法规、监察法规、地方法规、司法解释及相关立法资料，部分记录含 PDF。

## 预留方向

- `guiding_cases/`：最高人民法院指导性案例。
- `judgments/`：裁判文书或案例文书，需确认来源、授权和访问限制。
""",
    )


def with_limit_per_category(config: FlkCrawlConfig, limit: int | None) -> FlkCrawlConfig:
    if limit is None:
        return config
    return replace(
        config,
        category_specs=[replace(spec, limit=limit) for spec in config.category_specs],
    )
