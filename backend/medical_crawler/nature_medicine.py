from __future__ import annotations

import hashlib
import json
import re
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup


NATURE_BASE_URL = "https://www.nature.com"
NATURE_MEDICINE_ARCHIVE = f"{NATURE_BASE_URL}/nm/articles"


@dataclass(frozen=True)
class NatureMedicineConfig:
    output_root: Path
    min_year: int = 2022
    max_year: int = datetime.now(UTC).year
    max_records: int = 120
    sleep_seconds: float = 0.1
    timeout_seconds: float = 60.0
    trust_env: bool = False

    def normalized(self) -> "NatureMedicineConfig":
        if self.min_year < 1900:
            raise ValueError("min_year is invalid")
        if self.max_year < self.min_year:
            raise ValueError("max_year must be >= min_year")
        if self.max_records < 1:
            raise ValueError("max_records must be at least 1")
        if self.sleep_seconds < 0:
            raise ValueError("sleep_seconds cannot be negative")
        return self


@dataclass(frozen=True)
class NatureMedicineSummary:
    output_root: Path
    articles_seen: int
    articles_written: int
    pdf_downloaded: int
    pdf_skipped: int
    skipped_existing: int
    skipped_errors: int
    manifest_path: Path


class NatureApi(Protocol):
    def get_text(self, url: str) -> str:
        ...

    def get_bytes(self, url: str) -> bytes:
        ...


class NatureHttpApi:
    def __init__(self, config: NatureMedicineConfig) -> None:
        self.client = httpx.Client(
            timeout=config.timeout_seconds,
            follow_redirects=True,
            trust_env=config.trust_env,
            headers={"User-Agent": "Skill-First-Hybrid-RAG nature crawler/1.0"},
        )

    def close(self) -> None:
        self.client.close()

    def get_text(self, url: str) -> str:
        response = self.client.get(url)
        response.raise_for_status()
        return response.text

    def get_bytes(self, url: str) -> bytes:
        response = self.client.get(url)
        response.raise_for_status()
        return response.content


def safe_filename(value: str, *, fallback: str = "document", max_length: int = 96) -> str:
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]+', "_", value)
    cleaned = re.sub(r"\s+", "_", cleaned).strip("._ ")
    cleaned = cleaned or fallback
    if len(cleaned) <= max_length:
        return cleaned
    suffix = Path(cleaned).suffix
    if suffix and len(suffix) < max_length // 2:
        return f"{Path(cleaned).stem[: max_length - len(suffix)]}{suffix}"
    return cleaned[:max_length]


def article_archive_url(year: int, page: int) -> str:
    return f"{NATURE_MEDICINE_ARCHIVE}?sort=PubDate&year={year}&page={page}"


def parse_archive_article_urls(html: str, base_url: str = NATURE_BASE_URL) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    urls: list[str] = []
    seen: set[str] = set()
    for anchor in soup.select('a[href*="/articles/"]'):
        href = anchor.get("href")
        if not href:
            continue
        absolute = urljoin(base_url, href)
        if absolute in seen:
            continue
        seen.add(absolute)
        urls.append(absolute)
    return urls


def parse_article_page(html: str, url: str) -> dict[str, Any]:
    soup = BeautifulSoup(html, "html.parser")
    title = ""
    for selector in ['meta[name="citation_title"]', 'meta[name="dc.title"]', 'meta[property="og:title"]']:
        node = soup.select_one(selector)
        if node and node.get("content"):
            title = node.get("content", "").strip()
            break
    if not title:
        title_node = soup.select_one("title")
        title = title_node.get_text(" ", strip=True) if title_node else ""
    pdf_url = ""
    node = soup.select_one('meta[name="citation_pdf_url"]')
    if node and node.get("content"):
        pdf_url = node["content"].strip()
    else:
        link = soup.select_one('a[href$=".pdf"]')
        if link and link.get("href"):
            pdf_url = urljoin(NATURE_BASE_URL, link["href"])

    date = ""
    for selector in ['meta[name="dc.date"]', 'meta[name="citation_online_date"]', 'meta[name="prism.publicationDate"]']:
        node = soup.select_one(selector)
        if node and node.get("content"):
            date = node["content"].strip()
            break

    doi = ""
    node = soup.select_one('meta[name="citation_doi"]')
    if node and node.get("content"):
        doi = node["content"].strip()
    if not doi:
        identifier = soup.select_one('meta[name="dc.identifier"]')
        if identifier and identifier.get("content", "").startswith("doi:"):
            doi = identifier["content"].split("doi:", 1)[1]

    article_type = ""
    node = soup.select_one('meta[name="citation_article_type"]')
    if node and node.get("content"):
        article_type = node["content"].strip()
    source = ""
    node = soup.select_one('meta[name="dc.source"]')
    if node and node.get("content"):
        source = node["content"].strip()

    year = None
    if date:
        match = re.match(r"(\d{4})", date)
        if match:
            year = int(match.group(1))

    return {
        "title": title,
        "url": url,
        "pdf_url": pdf_url,
        "date": date,
        "year": year,
        "doi": doi,
        "article_type": article_type,
        "source": source,
    }


def article_dir(output_root: Path, article: dict[str, Any]) -> Path:
    title = safe_filename(article.get("title") or "nature_article", fallback="nature_article", max_length=64)
    digest_source = article.get("doi") or article.get("url") or title
    digest = hashlib.sha1(str(digest_source).encode("utf-8")).hexdigest()[:10]
    prefix = str(article.get("year") or "undated")
    return output_root / f"{prefix}_{digest}_{title}"


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.rstrip() + "\n", encoding="utf-8-sig")


def archive_title(year: int) -> str:
    return f"Nature Medicine {year}"


def render_index(manifest: dict[str, Any]) -> str:
    return f"""# Nature Medicine 医学文献

来源：Nature Medicine

国家/地区：International

资料类型：原始网页与可下载 PDF

## 统计

- `articles_written`：{manifest.get("articles_written", 0)}
- `pdf_downloaded`：{manifest.get("pdf_downloaded", 0)}
- `pdf_skipped`：{manifest.get("pdf_skipped", 0)}

## 说明

- 优先保留原始 `html`
- 只有能直接下载到的 `pdf` 才落盘
- 2022 年以前的条目默认跳过
"""


def crawl_nature_medicine(config: NatureMedicineConfig, *, api: NatureApi | None = None) -> NatureMedicineSummary:
    config = config.normalized()
    config.output_root.mkdir(parents=True, exist_ok=True)
    own_api = NatureHttpApi(config) if api is None else None
    nature_api = api or own_api
    assert nature_api is not None

    articles_seen = 0
    articles_written = 0
    pdf_downloaded = 0
    pdf_skipped = 0
    skipped_existing = 0
    skipped_errors = 0
    seen_urls: set[str] = set()

    try:
        for year in range(config.max_year, config.min_year - 1, -1):
            page = 1
            while articles_seen < config.max_records:
                try:
                    archive_html = nature_api.get_text(article_archive_url(year, page))
                except Exception:
                    break

                article_urls = parse_archive_article_urls(archive_html)
                if not article_urls:
                    break

                new_on_page = 0
                for article_url in article_urls:
                    if articles_seen >= config.max_records:
                        break
                    if article_url in seen_urls:
                        continue
                    seen_urls.add(article_url)
                    articles_seen += 1
                    new_on_page += 1
                    try:
                        html = nature_api.get_text(article_url)
                        article = parse_article_page(html, article_url)
                    except Exception:
                        skipped_errors += 1
                        continue
                    if article.get("year") is not None and int(article["year"]) < config.min_year:
                        continue

                    target_dir = article_dir(config.output_root, article)
                    html_path = target_dir / "source.html"
                    if html_path.exists():
                        skipped_existing += 1
                        continue

                    write_json(target_dir / "metadata.json", article)
                    write_text(html_path, html)
                    articles_written += 1

                    pdf_url = str(article.get("pdf_url") or "")
                    if pdf_url:
                        try:
                            content = nature_api.get_bytes(pdf_url)
                            if content[:4] == b"%PDF":
                                (target_dir / "source.pdf").write_bytes(content)
                                pdf_downloaded += 1
                            else:
                                pdf_skipped += 1
                        except Exception:
                            pdf_skipped += 1
                    else:
                        pdf_skipped += 1

                    if config.sleep_seconds:
                        time.sleep(config.sleep_seconds)

                if new_on_page == 0:
                    break
                page += 1
                if new_on_page < 20:
                    break
    finally:
        if own_api is not None:
            own_api.close()

    manifest_path = config.output_root / "manifest.json"
    manifest = {
        "generated_at": datetime.now(UTC).isoformat(),
        "source": {"name": "Nature Medicine", "url": NATURE_BASE_URL, "country": "International"},
        "articles_seen": articles_seen,
        "articles_written": articles_written,
        "pdf_downloaded": pdf_downloaded,
        "pdf_skipped": pdf_skipped,
        "skipped_existing": skipped_existing,
        "skipped_errors": skipped_errors,
    }
    write_json(manifest_path, manifest)
    write_text(config.output_root / "index.md", render_index(manifest))
    return NatureMedicineSummary(
        output_root=config.output_root,
        articles_seen=articles_seen,
        articles_written=articles_written,
        pdf_downloaded=pdf_downloaded,
        pdf_skipped=pdf_skipped,
        skipped_existing=skipped_existing,
        skipped_errors=skipped_errors,
        manifest_path=manifest_path,
    )
