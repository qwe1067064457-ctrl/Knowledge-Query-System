from __future__ import annotations

import json
import sys
import uuid
from pathlib import Path
from typing import Any, Iterator

import pytest


ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from legal_crawler.courtlistener import (
    CourtListenerConfig,
    JsonlLegalDocStore,
    classify_legal_document,
    crawl_courtlistener_opinions,
    normalize_opinion,
)


TEST_TMP_ROOT = Path(__file__).resolve().parent / ".test_tmp"


@pytest.fixture
def workspace() -> Path:
    path = TEST_TMP_ROOT / f"case_{uuid.uuid4().hex}"
    path.mkdir(parents=True, exist_ok=False)
    return path


class FakeClient:
    def __init__(self, pages: list[dict[str, Any]]) -> None:
        self.pages = pages

    def iter_opinion_pages(self, config: CourtListenerConfig) -> Iterator[dict[str, Any]]:
        yield from self.pages


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_normalize_opinion_accepts_html_and_cluster_metadata() -> None:
    document = normalize_opinion(
        {
            "id": 123,
            "html_with_citations": "<p>Contract liability <b>analysis</b>.</p>",
            "cluster": {
                "case_name": "Acme v. Example",
                "absolute_url": "/opinion/123/acme-v-example/",
                "date_filed": "2024-01-02",
                "docket_number": "24-1",
            },
        },
        collected_at="2026-05-10T00:00:00+00:00",
    )

    assert document is not None
    assert document.source_id == "123"
    assert document.title == "Acme v. Example"
    assert document.source_url == "https://www.courtlistener.com/opinion/123/acme-v-example/"
    assert document.date_filed == "2024-01-02"
    assert document.docket_number == "24-1"
    assert document.category == "contract"
    assert document.content == "Contract liability analysis ."


def test_normalize_opinion_rejects_empty_content() -> None:
    assert normalize_opinion({"id": 456, "cluster": {"case_name": "No Text Case"}}) is None


def test_classify_legal_document_detects_criminal_topic() -> None:
    category = classify_legal_document(
        "State v. Example",
        "The defendant challenges the criminal conviction and sentencing order.",
    )

    assert category == "criminal"


def test_classify_legal_document_falls_back_to_general() -> None:
    category = classify_legal_document("Short docket entry", "No strong topic words here.")

    assert category == "general"


def test_jsonl_store_appends_unique_document(workspace: Path) -> None:
    output = workspace / "legal_docs.jsonl"
    document = normalize_opinion({"id": 1, "plain_text": "A valid legal opinion."})
    assert document is not None

    store = JsonlLegalDocStore(output)

    assert store.append(document) is True
    rows = read_jsonl(output)
    assert len(rows) == 1
    assert rows[0]["source_id"] == "1"


def test_jsonl_store_skips_duplicate_document(workspace: Path) -> None:
    output = workspace / "legal_docs.jsonl"
    document = normalize_opinion({"id": 1, "plain_text": "A valid legal opinion."})
    assert document is not None
    store = JsonlLegalDocStore(output)

    assert store.append(document) is True
    assert store.append(document) is False

    assert len(read_jsonl(output)) == 1


def test_jsonl_store_writes_category_split_file(workspace: Path) -> None:
    output = workspace / "legal_docs.jsonl"
    document = normalize_opinion({"id": 1, "plain_text": "The contract breach caused damages."})
    assert document is not None

    store = JsonlLegalDocStore(output, split_by_category=True)

    assert store.append(document) is True
    split_path = workspace / "by_category" / "contract.jsonl"
    assert split_path.exists()
    assert read_jsonl(split_path)[0]["source_id"] == "1"


def test_crawler_writes_until_limit_across_pages(workspace: Path) -> None:
    output = workspace / "legal_docs.jsonl"
    client = FakeClient(
        [
            {"results": [{"id": 1, "plain_text": "First opinion."}]},
            {
                "results": [
                    {"id": 2, "plain_text": "Second opinion."},
                    {"id": 3, "plain_text": "Third opinion."},
                ]
            },
        ]
    )

    summary = crawl_courtlistener_opinions(
        CourtListenerConfig(output_path=output, limit=2, sleep_seconds=0),
        client=client,
    )

    assert summary.fetched == 2
    assert summary.written == 2
    assert [row["source_id"] for row in read_jsonl(output)] == ["1", "2"]


def test_crawler_counts_empty_and_duplicate_results(workspace: Path) -> None:
    output = workspace / "legal_docs.jsonl"
    client = FakeClient(
        [
            {
                "results": [
                    {"id": 1, "plain_text": "First opinion."},
                    {"id": 1, "plain_text": "First opinion."},
                    {"id": 2},
                ]
            }
        ]
    )

    summary = crawl_courtlistener_opinions(
        CourtListenerConfig(output_path=output, limit=10, sleep_seconds=0),
        client=client,
    )

    assert summary.fetched == 3
    assert summary.written == 1
    assert summary.skipped_duplicate == 1
    assert summary.skipped_empty == 1


def test_config_rejects_invalid_limit(workspace: Path) -> None:
    with pytest.raises(ValueError, match="limit"):
        CourtListenerConfig(output_path=workspace / "out.jsonl", limit=0).normalized()


def test_config_caps_page_size(workspace: Path) -> None:
    config = CourtListenerConfig(output_path=workspace / "out.jsonl", page_size=500).normalized()

    assert config.page_size == 100


def test_config_keeps_split_by_category_flag(workspace: Path) -> None:
    config = CourtListenerConfig(output_path=workspace / "out.jsonl", split_by_category=True).normalized()

    assert config.split_by_category is True


def test_config_ignores_environment_proxy_by_default(workspace: Path) -> None:
    config = CourtListenerConfig(output_path=workspace / "out.jsonl").normalized()

    assert config.trust_env is False
