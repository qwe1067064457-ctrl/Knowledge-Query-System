from __future__ import annotations

import hashlib
import json
import re
import time
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Iterable, Iterator, Protocol

import httpx


DEFAULT_BASE_URL = "https://www.courtlistener.com/api/rest/v4"


class OpinionPageClient(Protocol):
    def iter_opinion_pages(self, config: "CourtListenerConfig") -> Iterator[dict[str, Any]]:
        ...


@dataclass(frozen=True)
class CourtListenerConfig:
    output_path: Path
    limit: int = 10_000
    court: str | None = None
    page_size: int = 100
    base_url: str = DEFAULT_BASE_URL
    token: str | None = None
    sleep_seconds: float = 75.0
    timeout_seconds: float = 30.0
    include_raw: bool = False
    split_by_category: bool = False
    trust_env: bool = False

    def normalized(self) -> "CourtListenerConfig":
        if self.limit < 1:
            raise ValueError("limit must be at least 1")
        if self.page_size < 1:
            raise ValueError("page_size must be at least 1")
        if self.sleep_seconds < 0:
            raise ValueError("sleep_seconds cannot be negative")
        return CourtListenerConfig(
            output_path=self.output_path,
            limit=self.limit,
            court=self.court.strip() if self.court else None,
            page_size=min(self.page_size, 100),
            base_url=self.base_url.rstrip("/"),
            token=self.token,
            sleep_seconds=self.sleep_seconds,
            timeout_seconds=self.timeout_seconds,
            include_raw=self.include_raw,
            split_by_category=self.split_by_category,
            trust_env=self.trust_env,
        )


@dataclass(frozen=True)
class LegalDocument:
    source: str
    source_id: str
    source_url: str
    title: str
    court: str
    date_filed: str
    docket_number: str
    category: str
    content: str
    content_sha256: str
    collected_at: str
    raw: dict[str, Any]

    def to_json_line(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False, sort_keys=True)


@dataclass(frozen=True)
class CrawlSummary:
    fetched: int
    written: int
    skipped_duplicate: int
    skipped_empty: int
    output_path: Path
    category_counts: dict[str, int]


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._chunks: list[str] = []

    def handle_data(self, data: str) -> None:
        if data:
            self._chunks.append(data)

    def get_text(self) -> str:
        return normalize_whitespace(" ".join(self._chunks))


def html_to_text(value: str) -> str:
    parser = _TextExtractor()
    parser.feed(value)
    return parser.get_text()


def normalize_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def first_text(*values: Any) -> str:
    for value in values:
        if value is None:
            continue
        text = normalize_whitespace(str(value))
        if text:
            return text
    return ""


def extract_content(opinion: dict[str, Any]) -> str:
    plain = first_text(opinion.get("plain_text"))
    if plain:
        return plain

    html = first_text(
        opinion.get("html_with_citations"),
        opinion.get("html"),
        opinion.get("html_columbia"),
        opinion.get("html_lawbox"),
        opinion.get("xml_harvard"),
    )
    if html:
        return html_to_text(html)
    return ""


def classify_legal_document(title: str, content: str) -> str:
    haystack = f"{title}\n{content[:8000]}".lower()
    category_keywords = [
        (
            "criminal",
            [
                "criminal",
                "habeas",
                "sentencing",
                "defendant",
                "conviction",
                "probable cause",
                "fourth amendment",
            ],
        ),
        (
            "constitutional",
            [
                "constitutional",
                "first amendment",
                "second amendment",
                "due process",
                "equal protection",
                "commerce clause",
            ],
        ),
        (
            "contract",
            [
                "contract",
                "breach",
                "agreement",
                "arbitration",
                "lease",
                "warranty",
                "specific performance",
            ],
        ),
        (
            "tort",
            [
                "tort",
                "negligence",
                "liability",
                "injury",
                "damages",
                "malpractice",
                "wrongful death",
            ],
        ),
        (
            "employment",
            [
                "employment",
                "employee",
                "employer",
                "discrimination",
                "retaliation",
                "wage",
                "labor",
            ],
        ),
        (
            "intellectual_property",
            [
                "patent",
                "copyright",
                "trademark",
                "trade secret",
                "infringement",
            ],
        ),
        (
            "tax",
            [
                "tax",
                "irs",
                "internal revenue",
                "deduction",
                "deficiency",
            ],
        ),
        (
            "bankruptcy",
            [
                "bankruptcy",
                "debtor",
                "creditor",
                "discharge",
                "chapter 7",
                "chapter 11",
            ],
        ),
        (
            "immigration",
            [
                "immigration",
                "asylum",
                "removal",
                "deportation",
                "visa",
                "noncitizen",
            ],
        ),
        (
            "family",
            [
                "divorce",
                "custody",
                "child support",
                "adoption",
                "marriage",
                "domestic relations",
            ],
        ),
        (
            "administrative",
            [
                "agency",
                "administrative",
                "regulation",
                "rulemaking",
                "commission",
            ],
        ),
        (
            "evidence_procedure",
            [
                "evidence",
                "procedure",
                "jurisdiction",
                "summary judgment",
                "motion to dismiss",
                "class action",
            ],
        ),
    ]

    best_category = "general"
    best_score = 0
    for category, keywords in category_keywords:
        score = sum(1 for keyword in keywords if keyword in haystack)
        if score > best_score:
            best_category = category
            best_score = score

    return best_category


def _cluster_value(opinion: dict[str, Any], key: str) -> str:
    cluster = opinion.get("cluster")
    if isinstance(cluster, dict):
        return first_text(cluster.get(key))
    return ""


def _absolute_courtlistener_url(path_or_url: str) -> str:
    if not path_or_url:
        return ""
    if path_or_url.startswith("http://") or path_or_url.startswith("https://"):
        return path_or_url
    if path_or_url.startswith("/"):
        return f"https://www.courtlistener.com{path_or_url}"
    return path_or_url


def normalize_opinion(
    opinion: dict[str, Any],
    *,
    collected_at: str | None = None,
    include_raw: bool = False,
) -> LegalDocument | None:
    content = extract_content(opinion)
    if not content:
        return None

    opinion_id = first_text(opinion.get("id"), opinion.get("resource_uri"))
    if not opinion_id:
        opinion_id = hashlib.sha256(content.encode("utf-8")).hexdigest()

    source_url = first_text(
        opinion.get("absolute_url"),
        _cluster_value(opinion, "absolute_url"),
        opinion.get("cluster"),
        opinion.get("resource_uri"),
    )

    title = first_text(
        opinion.get("case_name"),
        _cluster_value(opinion, "case_name"),
        _cluster_value(opinion, "case_name_full"),
        f"CourtListener opinion {opinion_id}",
    )

    return LegalDocument(
        source="courtlistener",
        source_id=opinion_id,
        source_url=_absolute_courtlistener_url(source_url),
        title=title,
        court=first_text(opinion.get("court"), _cluster_value(opinion, "court")),
        date_filed=first_text(opinion.get("date_filed"), _cluster_value(opinion, "date_filed")),
        docket_number=first_text(opinion.get("docket_number"), _cluster_value(opinion, "docket_number")),
        category=classify_legal_document(title, content),
        content=content,
        content_sha256=hashlib.sha256(content.encode("utf-8")).hexdigest(),
        collected_at=collected_at or datetime.now(UTC).isoformat(),
        raw=opinion if include_raw else {},
    )


class JsonlLegalDocStore:
    def __init__(self, path: Path, *, split_by_category: bool = False) -> None:
        self.path = path
        self.split_by_category = split_by_category
        self._seen_ids: set[str] | None = None

    def load_seen_ids(self) -> set[str]:
        if self._seen_ids is not None:
            return self._seen_ids

        seen: set[str] = set()
        if self.path.exists():
            with self.path.open("r", encoding="utf-8") as handle:
                for line in handle:
                    if not line.strip():
                        continue
                    try:
                        payload = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    source_id = first_text(payload.get("source_id"))
                    if source_id:
                        seen.add(source_id)

        self._seen_ids = seen
        return seen

    def append(self, document: LegalDocument) -> bool:
        seen = self.load_seen_ids()
        if document.source_id in seen:
            return False

        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(document.to_json_line())
            handle.write("\n")

        if self.split_by_category:
            category_path = self.path.parent / "by_category" / f"{safe_filename(document.category)}.jsonl"
            category_path.parent.mkdir(parents=True, exist_ok=True)
            with category_path.open("a", encoding="utf-8") as handle:
                handle.write(document.to_json_line())
                handle.write("\n")

        seen.add(document.source_id)
        return True


class CourtListenerClient:
    def __init__(self) -> None:
        pass

    def iter_opinion_pages(self, config: CourtListenerConfig) -> Iterator[dict[str, Any]]:
        config = config.normalized()
        headers = {"User-Agent": "Skill-First-Hybrid-RAG legal-doc-crawler/1.0"}
        if config.token:
            headers["Authorization"] = f"Token {config.token}"

        params: dict[str, Any] = {
            "page_size": config.page_size,
        }
        if config.court:
            params["cluster__docket__court"] = config.court
        next_url: str | None = f"{config.base_url}/opinions/"

        with httpx.Client(
            headers=headers,
            timeout=config.timeout_seconds,
            follow_redirects=True,
            trust_env=config.trust_env,
        ) as client:
            while next_url:
                response = client.get(next_url, params=params if next_url.endswith("/opinions/") else None)
                response.raise_for_status()
                page = response.json()
                yield page
                next_url = page.get("next")
                params = {}
                if next_url and config.sleep_seconds:
                    time.sleep(config.sleep_seconds)


def iter_page_results(page: dict[str, Any]) -> Iterable[dict[str, Any]]:
    results = page.get("results", [])
    if not isinstance(results, list):
        return []
    return [item for item in results if isinstance(item, dict)]


def safe_filename(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9_-]+", "_", value).strip("_").lower()
    return slug or "general"


def crawl_courtlistener_opinions(
    config: CourtListenerConfig,
    *,
    client: OpinionPageClient | None = None,
    store: JsonlLegalDocStore | None = None,
) -> CrawlSummary:
    config = config.normalized()
    page_client = client or CourtListenerClient()
    doc_store = store or JsonlLegalDocStore(config.output_path, split_by_category=config.split_by_category)

    fetched = 0
    written = 0
    skipped_duplicate = 0
    skipped_empty = 0
    category_counts: dict[str, int] = {}

    for page in page_client.iter_opinion_pages(config):
        for opinion in iter_page_results(page):
            if fetched >= config.limit:
                return CrawlSummary(fetched, written, skipped_duplicate, skipped_empty, config.output_path, category_counts)

            fetched += 1
            document = normalize_opinion(opinion, include_raw=config.include_raw)
            if document is None:
                skipped_empty += 1
                continue

            if doc_store.append(document):
                written += 1
                category_counts[document.category] = category_counts.get(document.category, 0) + 1
            else:
                skipped_duplicate += 1

    return CrawlSummary(fetched, written, skipped_duplicate, skipped_empty, config.output_path, category_counts)
