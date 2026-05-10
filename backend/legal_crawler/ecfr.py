from __future__ import annotations

import hashlib
import json
import re
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterator

import httpx

from .courtlistener import JsonlLegalDocStore, LegalDocument, normalize_whitespace, safe_filename


ECFR_BASE_URL = "https://www.ecfr.gov/api/versioner/v1"
ECFR_WEB_BASE_URL = "https://www.ecfr.gov/current"


@dataclass(frozen=True)
class EcfrConfig:
    output_path: Path
    limit: int = 10_000
    base_url: str = ECFR_BASE_URL
    sleep_seconds: float = 1.0
    timeout_seconds: float = 120.0
    split_by_category: bool = True
    trust_env: bool = False

    def normalized(self) -> "EcfrConfig":
        if self.limit < 1:
            raise ValueError("limit must be at least 1")
        if self.sleep_seconds < 0:
            raise ValueError("sleep_seconds cannot be negative")
        return EcfrConfig(
            output_path=self.output_path,
            limit=self.limit,
            base_url=self.base_url.rstrip("/"),
            sleep_seconds=self.sleep_seconds,
            timeout_seconds=self.timeout_seconds,
            split_by_category=self.split_by_category,
            trust_env=self.trust_env,
        )


@dataclass(frozen=True)
class EcfrTitle:
    number: int
    name: str
    issue_date: str


@dataclass(frozen=True)
class EcfrCrawlSummary:
    titles_fetched: int
    sections_seen: int
    written: int
    skipped_duplicate: int
    skipped_empty: int
    output_path: Path
    category_counts: dict[str, int]


class EcfrClient:
    def fetch_titles(self, config: EcfrConfig) -> list[EcfrTitle]:
        config = config.normalized()
        with httpx.Client(timeout=config.timeout_seconds, follow_redirects=True, trust_env=config.trust_env) as client:
            response = client.get(f"{config.base_url}/titles.json")
            response.raise_for_status()
            payload = response.json()

        titles: list[EcfrTitle] = []
        for item in payload.get("titles", []):
            if not isinstance(item, dict):
                continue
            number = item.get("number")
            issue_date = item.get("latest_issue_date") or item.get("latest_amended_on")
            if not isinstance(number, int) or not issue_date:
                continue
            titles.append(EcfrTitle(number=number, name=str(item.get("name", "")).strip(), issue_date=str(issue_date)))
        return titles

    def fetch_title_xml(self, config: EcfrConfig, title: EcfrTitle) -> str:
        config = config.normalized()
        url = f"{config.base_url}/full/{title.issue_date}/title-{title.number}.xml"
        with httpx.Client(timeout=config.timeout_seconds, follow_redirects=True, trust_env=config.trust_env) as client:
            response = client.get(url)
            response.raise_for_status()
            return response.text


def classify_ecfr_section(title_name: str, section_title: str, content: str) -> str:
    haystack = f"{title_name}\n{section_title}\n{content[:4000]}".lower()
    title = title_name.lower()

    title_rules = [
        ("tax", ["internal revenue", "customs duties"]),
        ("employment_labor", ["labor", "employees' benefits"]),
        ("health", ["public health", "food and drugs"]),
        ("environment", ["protection of environment"]),
        ("transportation", ["transportation", "highways", "navigation", "shipping"]),
        ("agriculture", ["agriculture", "animals and animal products"]),
        ("finance", ["banks and banking", "commodity and securities", "money and finance"]),
        ("energy", ["energy", "mineral resources"]),
        ("telecommunications", ["telecommunication"]),
        ("housing", ["housing and urban development"]),
        ("education", ["education"]),
        ("defense_security", ["national defense", "homeland security", "aliens and nationality"]),
        ("government_administration", ["administrative personnel", "general provisions", "federal elections"]),
    ]
    for category, keywords in title_rules:
        if any(keyword in title for keyword in keywords):
            return category

    keyword_rules = [
        ("employment_labor", ["employee", "employer", "wage", "labor", "workplace"]),
        ("tax", ["tax", "internal revenue", "deduction"]),
        ("finance", ["bank", "securities", "credit", "loan", "insurance"]),
        ("health", ["health", "drug", "medical", "patient", "hospital"]),
        ("environment", ["environment", "emission", "pollution", "waste"]),
        ("transportation", ["transportation", "aircraft", "vehicle", "railroad", "vessel"]),
        ("defense_security", ["security", "defense", "classified", "immigration", "alien"]),
    ]
    for category, keywords in keyword_rules:
        if any(keyword in haystack for keyword in keywords):
            return category

    return "general_regulatory"


def extract_section_text(section: ET.Element) -> str:
    return normalize_whitespace(" ".join(text for text in section.itertext() if text and text.strip()))


def section_head(section: ET.Element) -> str:
    head = section.find("HEAD")
    if head is None:
        return ""
    return normalize_whitespace(" ".join(text for text in head.itertext() if text and text.strip()))


def iter_sections(xml_text: str) -> Iterator[ET.Element]:
    root = ET.fromstring(xml_text)
    for element in root.iter():
        if element.attrib.get("TYPE") == "SECTION":
            yield element


def section_url(title_number: int, section_number: str) -> str:
    if not section_number:
        return f"{ECFR_WEB_BASE_URL}/title-{title_number}"
    return f"{ECFR_WEB_BASE_URL}/title-{title_number}/section-{section_number}"


def normalize_ecfr_section(title: EcfrTitle, section: ET.Element, *, collected_at: str | None = None) -> LegalDocument | None:
    section_number = normalize_whitespace(section.attrib.get("N", ""))
    content = extract_section_text(section)
    if not section_number or not content:
        return None

    head = section_head(section)
    doc_title = head or f"Title {title.number} Section {section_number}"
    source_id = f"ecfr:title-{title.number}:section-{section_number}"
    category = classify_ecfr_section(title.name, doc_title, content)

    return LegalDocument(
        source="ecfr",
        source_id=source_id,
        source_url=section_url(title.number, section_number),
        title=doc_title,
        court="",
        date_filed=title.issue_date,
        docket_number=section_number,
        category=category,
        content=content,
        content_sha256=hashlib.sha256(content.encode("utf-8")).hexdigest(),
        collected_at=collected_at or datetime.now(UTC).isoformat(),
        raw={
            "title_number": title.number,
            "title_name": title.name,
            "issue_date": title.issue_date,
            "section_number": section_number,
        },
    )


def write_category_manifest(output_path: Path, category_counts: dict[str, int]) -> Path:
    manifest_path = output_path.parent / "category_manifest.json"
    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "output_path": str(output_path),
        "categories": {
            category: {
                "count": count,
                "path": str(output_path.parent / "by_category" / f"{safe_filename(category)}.jsonl"),
            }
            for category, count in sorted(category_counts.items())
        },
    }
    manifest_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest_path


def crawl_ecfr_sections(config: EcfrConfig, *, client: EcfrClient | None = None) -> EcfrCrawlSummary:
    config = config.normalized()
    ecfr_client = client or EcfrClient()
    store = JsonlLegalDocStore(config.output_path, split_by_category=config.split_by_category)

    titles_fetched = 0
    sections_seen = 0
    written = 0
    skipped_duplicate = 0
    skipped_empty = 0
    category_counts: dict[str, int] = {}

    for title in ecfr_client.fetch_titles(config):
        if written >= config.limit:
            break

        xml_text = ecfr_client.fetch_title_xml(config, title)
        titles_fetched += 1

        for section in iter_sections(xml_text):
            if written >= config.limit:
                break

            sections_seen += 1
            document = normalize_ecfr_section(title, section)
            if document is None:
                skipped_empty += 1
                continue

            if store.append(document):
                written += 1
                category_counts[document.category] = category_counts.get(document.category, 0) + 1
            else:
                skipped_duplicate += 1

        if written < config.limit and config.sleep_seconds:
            time.sleep(config.sleep_seconds)

    write_category_manifest(config.output_path, category_counts)
    return EcfrCrawlSummary(
        titles_fetched=titles_fetched,
        sections_seen=sections_seen,
        written=written,
        skipped_duplicate=skipped_duplicate,
        skipped_empty=skipped_empty,
        output_path=config.output_path,
        category_counts=category_counts,
    )
