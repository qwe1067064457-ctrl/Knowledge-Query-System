from __future__ import annotations

import hashlib
import json
import re
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

from .china_flk import safe_cn_filename
from .courtlistener import first_text, normalize_whitespace


COURT_BASE_URL = "https://www.court.gov.cn"
GUIDING_CASE_LIST_URL = f"{COURT_BASE_URL}/fabu/gengduo/151.html"


@dataclass(frozen=True)
class CourtGuidingCaseConfig:
    output_root: Path
    pages: int = 12
    max_records: int | None = None
    sleep_seconds: float = 0.2
    timeout_seconds: float = 60.0
    trust_env: bool = False

    def normalized(self) -> "CourtGuidingCaseConfig":
        if self.pages < 1:
            raise ValueError("pages must be at least 1")
        if self.max_records is not None and self.max_records < 1:
            raise ValueError("max_records must be at least 1 when set")
        if self.sleep_seconds < 0:
            raise ValueError("sleep_seconds cannot be negative")
        return self


@dataclass(frozen=True)
class CourtGuidingCaseSummary:
    output_root: Path
    records_seen: int
    records_written: int
    skipped_existing: int
    skipped_errors: int
    manifest_path: Path


class CourtApi(Protocol):
    def get_text(self, url: str) -> str:
        ...


class CourtHttpApi:
    def __init__(self, config: CourtGuidingCaseConfig) -> None:
        self.config = config.normalized()
        self.client = httpx.Client(
            timeout=self.config.timeout_seconds,
            follow_redirects=True,
            trust_env=self.config.trust_env,
            headers={"User-Agent": "Skill-First-Hybrid-RAG court guiding case crawler/1.0"},
        )

    def close(self) -> None:
        self.client.close()

    def get_text(self, url: str) -> str:
        response = self.client.get(url)
        response.raise_for_status()
        response.encoding = response.encoding or "utf-8"
        return response.text


def guiding_case_list_urls(pages: int) -> list[str]:
    urls = [GUIDING_CASE_LIST_URL]
    urls.extend(f"{COURT_BASE_URL}/fabu/gengduo/151_{page}.html" for page in range(1, pages))
    return urls


def parse_guiding_case_links(html: str, *, base_url: str = COURT_BASE_URL) -> list[dict[str, str]]:
    soup = BeautifulSoup(html, "html.parser")
    links: list[dict[str, str]] = []
    seen: set[str] = set()
    for anchor in soup.select('a[href*="/fabu/xiangqing/"]'):
        title = normalize_whitespace(anchor.get_text(" ", strip=True))
        href = first_text(anchor.get("href"))
        if not title or "指导" not in title:
            continue
        url = urljoin(base_url, href)
        if url in seen:
            continue
        seen.add(url)
        links.append({"title": title, "url": url})
    return links


def parse_guiding_case_article(html: str, *, url: str, fallback_title: str) -> dict[str, Any]:
    soup = BeautifulSoup(html, "html.parser")
    title = normalize_whitespace(first_text(
        (soup.select_one(".title") or {}).get_text(" ", strip=True) if soup.select_one(".title") else "",
        fallback_title,
    ))
    detail_text = normalize_whitespace(
        (soup.select_one(".detail") or soup).get_text(" ", strip=True)
    )
    body_node = soup.select_one(".txt") or soup.select_one(".content") or soup.body or soup
    body = body_node.get_text("\n", strip=True)
    body_lines = [normalize_whitespace(line) for line in body.splitlines()]
    body = "\n".join(line for line in body_lines if line)

    source_match = re.search(r"来源：\s*(.*?)\s*发布时间：", detail_text)
    date_match = re.search(r"发布时间：\s*(\d{4}-\d{2}-\d{2}(?:\s+\d{2}:\d{2}:\d{2})?)", detail_text)
    return {
        "title": title,
        "url": url,
        "source": source_match.group(1).strip() if source_match else "最高人民法院",
        "published_at": date_match.group(1).strip() if date_match else "",
        "body": body,
    }


def case_dir(output_root: Path, article: dict[str, Any]) -> Path:
    published_at = first_text(article.get("published_at")).split(" ")[0].replace("-", "")
    prefix = published_at or "undated"
    digest = hashlib.sha1(first_text(article.get("url")).encode("utf-8")).hexdigest()[:10]
    title = safe_cn_filename(first_text(article.get("title"), digest), fallback=digest, max_length=36)
    return output_root / f"{prefix}_{digest}_{title}"


def render_case_markdown(article: dict[str, Any]) -> str:
    title = first_text(article.get("title"), "未命名指导性案例")
    return "\n".join(
        [
            "---",
            f'title: "{title}"',
            'source: "最高人民法院"',
            f'source_url: "{first_text(article.get("url"))}"',
            f'published_at: "{first_text(article.get("published_at"))}"',
            'document_type: "guiding_case"',
            "---",
            "",
            f"# {title}",
            "",
            f"- 来源：{first_text(article.get('source'), '最高人民法院')}",
            f"- 发布时间：{first_text(article.get('published_at'))}",
            f"- 原始页面：{first_text(article.get('url'))}",
            "",
            "## 正文",
            "",
            first_text(article.get("body")),
        ]
    ).rstrip() + "\n"


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.rstrip() + "\n", encoding="utf-8")


def render_guiding_case_index(manifest: dict[str, Any]) -> str:
    return f"""# 最高人民法院指导性案例

来源：最高人民法院

资料类型：指导性案例 HTML 正文

已写入记录数：{manifest.get("records_written", 0)}

## 目录说明

- 每个案例保存为一个独立目录。
- `metadata.json` 保存来源链接、发布时间和正文元数据。
- `case.md` 保存 agent 可直接读取的 Markdown 正文。
"""


def crawl_court_guiding_cases(
    config: CourtGuidingCaseConfig,
    *,
    api: CourtApi | None = None,
) -> CourtGuidingCaseSummary:
    config = config.normalized()
    config.output_root.mkdir(parents=True, exist_ok=True)
    own_api = CourtHttpApi(config) if api is None else None
    court_api = api or own_api
    assert court_api is not None

    records_seen = 0
    records_written = 0
    skipped_existing = 0
    skipped_errors = 0
    seen_urls: set[str] = set()

    try:
        for list_url in guiding_case_list_urls(config.pages):
            try:
                links = parse_guiding_case_links(court_api.get_text(list_url))
            except Exception:
                skipped_errors += 1
                continue

            for link in links:
                if config.max_records is not None and records_seen >= config.max_records:
                    break
                url = link["url"]
                if url in seen_urls:
                    continue
                seen_urls.add(url)
                records_seen += 1
                try:
                    html = court_api.get_text(url)
                    article = parse_guiding_case_article(
                        html,
                        url=url,
                        fallback_title=link["title"],
                    )
                except Exception:
                    skipped_errors += 1
                    continue

                target_dir = case_dir(config.output_root, article)
                metadata_path = target_dir / "metadata.json"
                if metadata_path.exists():
                    skipped_existing += 1

                payload = {
                    "source": "最高人民法院",
                    "source_url": url,
                    "document_type": "guiding_case",
                    "article": article,
                    "collected_at": datetime.now(UTC).isoformat(),
                }
                write_json(metadata_path, payload)
                write_text(target_dir / "source.html", html)
                write_text(target_dir / "case.md", render_case_markdown(article))
                records_written += 1

                if config.sleep_seconds:
                    time.sleep(config.sleep_seconds)

            if config.max_records is not None and records_seen >= config.max_records:
                break
    finally:
        if own_api is not None:
            own_api.close()

    manifest_path = config.output_root / "manifest.json"
    manifest = {
        "generated_at": datetime.now(UTC).isoformat(),
        "source": {
            "name": "最高人民法院",
            "url": COURT_BASE_URL,
            "country": "China",
        },
        "document_type": "guiding_case",
        "output_root": str(config.output_root),
        "records_seen": records_seen,
        "records_written": records_written,
        "skipped_existing": skipped_existing,
        "skipped_errors": skipped_errors,
    }
    write_json(manifest_path, manifest)
    write_text(config.output_root / "index.md", render_guiding_case_index(manifest))
    return CourtGuidingCaseSummary(
        output_root=config.output_root,
        records_seen=records_seen,
        records_written=records_written,
        skipped_existing=skipped_existing,
        skipped_errors=skipped_errors,
        manifest_path=manifest_path,
    )
