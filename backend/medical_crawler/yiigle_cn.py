from __future__ import annotations

import hashlib
import html as html_lib
import json
import re
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup


YIIGLE_BASE_URL = "https://rs.yiigle.com"
DEFAULT_JOURNAL_HOME = "http://zgjcyy.yiigle.com/"


@dataclass(frozen=True)
class YiigleCnConfig:
    output_root: Path
    journal_home_url: str = DEFAULT_JOURNAL_HOME
    min_year: int = 2022
    max_records: int = 10
    sleep_seconds: float = 0.1
    timeout_seconds: float = 60.0
    trust_env: bool = False
    refresh_existing: bool = False

    def normalized(self) -> "YiigleCnConfig":
        if self.min_year < 1900:
            raise ValueError("min_year is invalid")
        if self.max_records < 1:
            raise ValueError("max_records must be at least 1")
        if self.sleep_seconds < 0:
            raise ValueError("sleep_seconds cannot be negative")
        return self


@dataclass(frozen=True)
class YiigleCnSummary:
    output_root: Path
    articles_seen: int
    articles_written: int
    skipped_existing: int
    skipped_year: int
    skipped_errors: int
    manifest_path: Path


class YiigleApi(Protocol):
    def get_text(self, url: str) -> str:
        ...

    def get_binary(self, url: str) -> bytes:
        ...


class YiigleHttpApi:
    def __init__(self, config: YiigleCnConfig) -> None:
        self.client = httpx.Client(
            timeout=config.timeout_seconds,
            follow_redirects=True,
            trust_env=config.trust_env,
            headers={"User-Agent": "Skill-First-Hybrid-RAG yiigle crawler/1.0"},
        )

    def close(self) -> None:
        self.client.close()

    def get_text(self, url: str) -> str:
        response = self.client.get(url)
        response.raise_for_status()
        return response.text

    def get_binary(self, url: str) -> bytes:
        response = self.client.get(url)
        response.raise_for_status()
        return response.content


def safe_filename(value: str, *, fallback: str = "document", max_length: int = 72) -> str:
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]+', "_", value)
    cleaned = re.sub(r"\s+", "_", cleaned).strip("._ ")
    cleaned = cleaned or fallback
    return cleaned[:max_length]


def parse_home_article_links(html: str, base_url: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    links: list[str] = []
    seen: set[str] = set()
    for anchor in soup.select('a[href*="rs.yiigle.com/cmaid/"]'):
        href = anchor.get("href")
        if not href:
            continue
        absolute = urljoin(base_url, href)
        if absolute in seen:
            continue
        seen.add(absolute)
        links.append(absolute)
    return links


def meta_content(soup: BeautifulSoup, name: str) -> str:
    node = soup.select_one(f'meta[name="{name}"]')
    if not node:
        return ""
    return node.get("content", "").strip()


def meta_contents(soup: BeautifulSoup, name: str) -> list[str]:
    values: list[str] = []
    for node in soup.select(f'meta[name="{name}"]'):
        content = node.get("content", "").strip()
        if content:
            values.append(content)
    return values


def parse_keywords(raw: str) -> list[str]:
    if not raw:
        return []
    parts = [part.strip() for part in re.split(r"[;,；，]", raw) if part.strip()]
    return parts


def unique_texts(values: list[str]) -> list[str]:
    items: list[str] = []
    seen: set[str] = set()
    for value in values:
        normalized = normalize_text(value)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        items.append(normalized)
    return items


def normalize_text(value: str) -> str:
    value = html_lib.unescape(value or "")
    value = re.sub(r"\s+", " ", value).strip()
    return value


def extract_xml_data(html: str) -> str:
    match = re.search(r'xmlData:"((?:\\.|[^"])*)"', html)
    if not match:
        return ""
    raw = match.group(1)
    raw = raw.replace(r"\/", "/").replace(r"\"", '"').replace(r"\n", "\n").replace(r"\r", "\r").replace(r"\t", "\t")
    raw = re.sub(r"\\u([0-9a-fA-F]{4})", lambda item: chr(int(item.group(1), 16)), raw)
    raw = raw.replace(r"\\", "\\")
    return raw


def xml_tag_name(tag: str) -> str:
    if "}" in tag:
        return tag.split("}", 1)[1]
    return tag


def xml_text(node: ET.Element | None) -> str:
    if node is None:
        return ""
    return normalize_text(" ".join(text for text in node.itertext()))


def append_caption_blocks(node: ET.Element, blocks: list[str], *, heading_level: int) -> None:
    label = xml_text(node.find("label"))
    caption = xml_text(node.find("caption"))
    block = " ".join(part for part in [label, caption] if part)
    if block:
        blocks.append(f"{'#' * min(heading_level, 6)} {block}")


def collect_section_blocks(node: ET.Element, blocks: list[str], *, heading_level: int) -> None:
    for child in list(node):
        tag_name = xml_tag_name(child.tag)
        if tag_name == "sec":
            title = ""
            for grandchild in list(child):
                if xml_tag_name(grandchild.tag) == "title":
                    title = xml_text(grandchild)
                    break
            if title:
                blocks.append(f"{'#' * min(heading_level, 6)} {title}")
            collect_section_blocks(child, blocks, heading_level=heading_level + 1)
            continue
        if tag_name == "p":
            paragraph = xml_text(child)
            if paragraph:
                blocks.append(paragraph)
            continue
        if tag_name in {"table-wrap", "fig"}:
            append_caption_blocks(child, blocks, heading_level=heading_level)
            continue
        if tag_name in {"list", "list-item", "boxed-text"}:
            collect_section_blocks(child, blocks, heading_level=heading_level)


def extract_fulltext_body(xml_data: str) -> str:
    if not xml_data:
        return ""
    try:
        root = ET.fromstring(xml_data)
    except ET.ParseError:
        return ""
    body = None
    for node in root.iter():
        if xml_tag_name(node.tag) == "body":
            body = node
            break
    if body is None:
        return ""
    blocks: list[str] = []
    collect_section_blocks(body, blocks, heading_level=2)
    cleaned_blocks = [block for block in blocks if block]
    return "\n\n".join(cleaned_blocks).strip()


def extract_pdf_url(xml_data: str, *, base_url: str = YIIGLE_BASE_URL) -> str:
    if not xml_data:
        return ""
    match = re.search(r'content-type="pdf"[^>]*xlink:href="([^"]+)"', xml_data)
    if not match:
        return ""
    return urljoin(f"{base_url}/", match.group(1))


def extract_article_payload(html: str, url: str) -> dict[str, Any]:
    soup = BeautifulSoup(html, "html.parser")
    title = meta_content(soup, "citation_title") or meta_content(soup, "eprints.title")
    abstract = meta_content(soup, "citation_abstract") or meta_content(soup, "eprints.abstract")
    date = meta_content(soup, "citation_publication_date") or meta_content(soup, "eprints.date")
    journal = meta_content(soup, "citation_journal_title") or meta_content(soup, "eprints.publication")
    authors = unique_texts(meta_contents(soup, "citation_author"))

    keyword_values = meta_contents(soup, "citation_keyword")
    if keyword_values:
        keywords = unique_texts(keyword_values)
    else:
        keywords = unique_texts(parse_keywords(meta_content(soup, "keywords")))

    doi = meta_content(soup, "citation_doi")
    year = None
    if date:
        match = re.match(r"(\d{4})", date)
        if match:
            year = int(match.group(1))

    xml_data = extract_xml_data(html)
    fulltext_body = extract_fulltext_body(xml_data)
    body = fulltext_body or normalize_text(abstract)
    body_kind = "fulltext_xml" if fulltext_body else "abstract_only"
    pdf_url = extract_pdf_url(xml_data)

    return {
        "title": normalize_text(title),
        "url": url,
        "abstract": normalize_text(abstract),
        "body": body,
        "body_kind": body_kind,
        "date": date,
        "year": year,
        "journal": normalize_text(journal),
        "authors": authors,
        "keywords": keywords,
        "doi": normalize_text(doi),
        "pdf_url": pdf_url,
        "xml_available": bool(xml_data),
    }


def article_dir(output_root: Path, article: dict[str, Any]) -> Path:
    title = safe_filename(article.get("title") or "yiigle_article", fallback="yiigle_article")
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


def write_binary(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


def download_pdf(article: dict[str, Any], *, api: YiigleApi, target_path: Path) -> bool:
    pdf_url = article.get("pdf_url") or ""
    if not pdf_url:
        return False
    try:
        payload = api.get_binary(pdf_url)
    except Exception:
        return False
    if not payload.startswith(b"%PDF"):
        return False
    write_binary(target_path, payload)
    return True


def render_content_md(article: dict[str, Any]) -> str:
    keywords = "、".join(article.get("keywords") or [])
    authors = "、".join(article.get("authors") or [])
    pdf_line = article.get("pdf_url") or "未发现可直接下载的 PDF"
    return f"""# {article.get("title", "")}

- 来源：{article.get("journal", "中国基层医药")}
- 原始页面：{article.get("url", "")}
- 发表日期：{article.get("date", "")}
- 作者：{authors}
- 关键词：{keywords}
- 正文层类型：{article.get("body_kind", "")}
- PDF线索：{pdf_line}

## 摘要

{article.get("abstract", "")}

## 正文层

{article.get("body", "")}
"""


def render_index(manifest: dict[str, Any]) -> str:
    return f"""# 中国基层医药医学样本

来源：中国基层医药 / Yiigle

资料类型：原始网页 + 正文层

## 统计

- `articles_written`：{manifest.get("articles_written", 0)}
- `fulltext_xml`：{manifest.get("fulltext_xml", 0)}
- `pdf_downloaded`：{manifest.get("pdf_downloaded", 0)}
- `skipped_year`：{manifest.get("skipped_year", 0)}
- `skipped_errors`：{manifest.get("skipped_errors", 0)}

## 说明

- 保留原始 `source.html`
- 若页面内含 `xmlData`，正文层优先从全文 XML 抽取
- 若页面只暴露摘要元数据，则退化为摘要型正文层
- 检测到 PDF 线索时会尝试下载，下载失败不会影响 HTML 与正文层入库
"""


def crawl_yiigle_cn_articles(config: YiigleCnConfig, *, api: YiigleApi | None = None) -> YiigleCnSummary:
    config = config.normalized()
    config.output_root.mkdir(parents=True, exist_ok=True)
    own_api = YiigleHttpApi(config) if api is None else None
    yiigle_api = api or own_api
    assert yiigle_api is not None

    articles_seen = 0
    articles_written = 0
    skipped_existing = 0
    skipped_year = 0
    skipped_errors = 0
    fulltext_xml = 0
    pdf_downloaded = 0

    try:
        home_html = yiigle_api.get_text(config.journal_home_url)
        article_urls = parse_home_article_links(home_html, config.journal_home_url)
        for article_url in article_urls:
            if articles_seen >= config.max_records:
                break
            articles_seen += 1
            try:
                html = yiigle_api.get_text(article_url)
                article = extract_article_payload(html, article_url)
            except Exception:
                skipped_errors += 1
                continue
            if not article.get("abstract"):
                skipped_errors += 1
                continue
            if article.get("year") is not None and int(article["year"]) < config.min_year:
                skipped_year += 1
                continue

            target_dir = article_dir(config.output_root, article)
            html_path = target_dir / "source.html"
            if html_path.exists() and not config.refresh_existing:
                skipped_existing += 1
                continue

            if article.get("body_kind") == "fulltext_xml":
                fulltext_xml += 1

            write_json(target_dir / "metadata.json", article)
            write_text(html_path, html)
            write_text(target_dir / "content.md", render_content_md(article))
            if download_pdf(article, api=yiigle_api, target_path=target_dir / "source.pdf"):
                pdf_downloaded += 1
            articles_written += 1
            if config.sleep_seconds:
                time.sleep(config.sleep_seconds)
    finally:
        if own_api is not None:
            own_api.close()

    manifest_path = config.output_root / "manifest.json"
    manifest = {
        "generated_at": datetime.now(UTC).isoformat(),
        "source": {"name": "中国基层医药", "url": config.journal_home_url, "country": "China"},
        "articles_seen": articles_seen,
        "articles_written": articles_written,
        "skipped_existing": skipped_existing,
        "skipped_year": skipped_year,
        "skipped_errors": skipped_errors,
        "fulltext_xml": fulltext_xml,
        "pdf_downloaded": pdf_downloaded,
    }
    write_json(manifest_path, manifest)
    write_text(config.output_root / "index.md", render_index(manifest))
    return YiigleCnSummary(
        output_root=config.output_root,
        articles_seen=articles_seen,
        articles_written=articles_written,
        skipped_existing=skipped_existing,
        skipped_year=skipped_year,
        skipped_errors=skipped_errors,
        manifest_path=manifest_path,
    )
