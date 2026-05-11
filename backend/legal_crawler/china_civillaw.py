from __future__ import annotations

import hashlib
import json
import re
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

from .china_flk import safe_cn_filename
from .courtlistener import first_text, normalize_whitespace


CIVILLAW_BASE_URL = "https://www.civillaw.com.cn"
DEFAULT_LIST_URLS = [
    f"{CIVILLAW_BASE_URL}/lw/",
    f"{CIVILLAW_BASE_URL}/xs/",
    f"{CIVILLAW_BASE_URL}/yd/",
    f"{CIVILLAW_BASE_URL}/fs/",
    f"{CIVILLAW_BASE_URL}/pf/",
]
ARTICLE_PATTERNS = (
    "/t/?id=",
    "/lw/t/?id=",
    "/xs/t/?id=",
    "/yd/t/?id=",
    "/fs/t/?id=",
    "/pf/t/?id=",
)


@dataclass(frozen=True)
class CivilLawConfig:
    output_root: Path
    list_urls: list[str]
    min_year: int = 2022
    max_records: int = 200
    sleep_seconds: float = 0.1
    timeout_seconds: float = 45.0
    trust_env: bool = False

    def normalized(self) -> "CivilLawConfig":
        if self.max_records < 1:
            raise ValueError("max_records must be at least 1")
        if self.min_year < 1900:
            raise ValueError("min_year is invalid")
        if self.sleep_seconds < 0:
            raise ValueError("sleep_seconds cannot be negative")
        return self


@dataclass(frozen=True)
class CivilLawSummary:
    output_root: Path
    articles_seen: int
    articles_written: int
    skipped_existing: int
    skipped_year: int
    skipped_errors: int
    manifest_path: Path


class CivilLawApi(Protocol):
    def get_text(self, url: str) -> str:
        ...


class CivilLawHttpApi:
    def __init__(self, config: CivilLawConfig) -> None:
        self.client = httpx.Client(
            timeout=config.timeout_seconds,
            trust_env=config.trust_env,
            follow_redirects=True,
            headers={"User-Agent": "Skill-First-Hybrid-RAG civillaw crawler/1.0"},
        )

    def close(self) -> None:
        self.client.close()

    def get_text(self, url: str) -> str:
        response = self.client.get(url)
        response.raise_for_status()
        return response.text


def parse_list_links(html: str, base_url: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    urls: list[str] = []
    seen: set[str] = set()
    for anchor in soup.select("a[href]"):
        href = first_text(anchor.get("href"))
        if not href or not any(pattern in href for pattern in ARTICLE_PATTERNS):
            continue
        absolute = urljoin(base_url, href)
        if absolute in seen:
            continue
        seen.add(absolute)
        urls.append(absolute)
    return urls


def extract_year(html: str) -> int | None:
    candidates = re.findall(r"20\d{2}[-/.年]\s*\d{1,2}[-/.月]\s*\d{1,2}", html)
    if not candidates:
        candidates = re.findall(r"20\d{2}[-/.]\d{1,2}", html)
    for candidate in candidates:
        match = re.search(r"(20\d{2})", candidate)
        if match:
            return int(match.group(1))
    return None


def extract_title(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for selector in (".show_title", ".title", "h1", "title"):
        node = soup.select_one(selector)
        if node:
            title = normalize_whitespace(node.get_text(" ", strip=True))
            if title:
                return title
    return "untitled"


def article_dir(output_root: Path, url: str, title: str, year: int | None) -> Path:
    digest = hashlib.sha1(url.encode("utf-8")).hexdigest()[:10]
    prefix = str(year) if year else "undated"
    safe_title = safe_cn_filename(title, fallback=digest, max_length=48)
    return output_root / f"{prefix}_{digest}_{safe_title}"


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def crawl_civillaw_articles(config: CivilLawConfig, *, api: CivilLawApi | None = None) -> CivilLawSummary:
    config = config.normalized()
    config.output_root.mkdir(parents=True, exist_ok=True)
    own_api = CivilLawHttpApi(config) if api is None else None
    client = api or own_api
    assert client is not None

    articles_seen = 0
    articles_written = 0
    skipped_existing = 0
    skipped_year = 0
    skipped_errors = 0
    seen_urls: set[str] = set()

    try:
        for list_url in config.list_urls:
            try:
                article_urls = parse_list_links(client.get_text(list_url), list_url)
            except Exception:
                skipped_errors += 1
                continue

            for article_url in article_urls:
                if articles_seen >= config.max_records:
                    break
                if article_url in seen_urls:
                    continue
                seen_urls.add(article_url)
                articles_seen += 1
                try:
                    html = client.get_text(article_url)
                except Exception:
                    skipped_errors += 1
                    continue

                year = extract_year(html)
                if year is None or year < config.min_year:
                    skipped_year += 1
                    continue

                title = extract_title(html)
                target_dir = article_dir(config.output_root, article_url, title, year)
                if (target_dir / "source.html").exists():
                    skipped_existing += 1
                    continue

                metadata = {
                    "source": "中国民商法律网",
                    "source_url": article_url,
                    "title": title,
                    "year": year,
                    "collected_at": datetime.now(UTC).isoformat(),
                }
                write_json(target_dir / "metadata.json", metadata)
                write_text(target_dir / "source.html", html)
                articles_written += 1
                if config.sleep_seconds:
                    time.sleep(config.sleep_seconds)
            if articles_seen >= config.max_records:
                break
    finally:
        if own_api is not None:
            own_api.close()

    manifest_path = config.output_root / "manifest.json"
    manifest = {
        "generated_at": datetime.now(UTC).isoformat(),
        "source": {"name": "中国民商法律网", "url": CIVILLAW_BASE_URL, "country": "China"},
        "articles_seen": articles_seen,
        "articles_written": articles_written,
        "skipped_existing": skipped_existing,
        "skipped_year": skipped_year,
        "skipped_errors": skipped_errors,
    }
    write_json(manifest_path, manifest)
    return CivilLawSummary(
        output_root=config.output_root,
        articles_seen=articles_seen,
        articles_written=articles_written,
        skipped_existing=skipped_existing,
        skipped_year=skipped_year,
        skipped_errors=skipped_errors,
        manifest_path=manifest_path,
    )
