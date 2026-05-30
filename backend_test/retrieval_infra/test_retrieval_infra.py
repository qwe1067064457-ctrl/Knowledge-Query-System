from __future__ import annotations

import json
import sys
import shutil
import uuid
from contextlib import contextmanager
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = REPO_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from retrieval_infra.adapters import KnowledgeSourceAdapter, MemorySourceAdapter, WorkflowRetrievalAdapter
from retrieval_infra.chunking import TextChunker
from retrieval_infra.contracts import BuildCheckpoint, BuildRequest
from retrieval_infra.indexing import ChunkStore, LexicalIndex, ManifestStore, SimpleVectorIndex, StateStore
from retrieval_infra.indexing.repo_knowledge_manager import RepoKnowledgeIndexManager
from retrieval_infra.normalization import DocumentNormalizer
from retrieval_infra.parsing import SimpleTextParser
from retrieval_infra.query.repo_knowledge_retriever import RepoKnowledgeRetriever
from retrieval_infra.queue import WorkQueue


TEST_TMP_ROOT = Path(__file__).resolve().parent / ".test_tmp"


@contextmanager
def _local_temp_dir():
    TEST_TMP_ROOT.mkdir(parents=True, exist_ok=True)
    temp_dir = TEST_TMP_ROOT / f"case_{uuid.uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=False)
    try:
        yield temp_dir
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def local_tmp_path() -> Path:
    with _local_temp_dir() as temp_dir:
        yield temp_dir


def test_lexical_index_recalls_matching_chunks_and_rejects_missing_terms(local_tmp_path: Path) -> None:
    source = KnowledgeSourceAdapter().build_source_document(
        source_id="knowledge_general_ai",
        group_id="general",
        source_path="groups/general/knowledge/raw/ai/report.txt",
        content="Agent retrieval planning.\n\nTool orchestration and retrieval quality.",
        file_type="txt",
        metadata={"title": "AI report"},
        revision="rev-1",
    )
    parsed = SimpleTextParser().parse("doc_ai_1", source)
    normalized = DocumentNormalizer().normalize(parsed)
    chunks = TextChunker().chunk(normalized)

    chunk_store = ChunkStore(local_tmp_path / "chunk_store.sqlite")
    chunk_store.upsert_chunks(chunks)
    lexical = LexicalIndex(local_tmp_path / "lexical" / "term_postings.sqlite", local_tmp_path / "lexical" / "globals.json")
    lexical.rebuild(chunks)

    hits = lexical.query("agent retrieval", top_k=5)
    miss = lexical.query("cardiology", top_k=5)

    assert hits
    assert hits[0][0].startswith("chunk_")
    assert chunk_store.get_chunk_content(hits[0][0]) is not None
    assert miss == []


def test_manifest_store_switch_and_rollback_round_trip(local_tmp_path: Path) -> None:
    store = ManifestStore(local_tmp_path / "index_manifest.json")

    initial = store.load("knowledge")
    switched = store.switch("knowledge", active_slot="next", previous_slot="current", snapshot_id="snap_001")
    rolled_back = store.rollback("knowledge", active_slot="current", previous_slot="next", snapshot_id="snap_000")

    assert initial.active_slot == "current"
    assert switched.active_slot == "next"
    assert switched.previous_slot == "current"
    assert rolled_back.active_slot == "current"
    assert rolled_back.previous_slot == "next"


def test_state_store_persists_build_and_checkpoint(local_tmp_path: Path) -> None:
    store = StateStore(
        build_registry_path=local_tmp_path / "build_registry.jsonl",
        checkpoints_path=local_tmp_path / "checkpoints.json",
    )
    request = BuildRequest(
        build_id="build_001",
        group_id="general",
        namespace="knowledge",
        mode="incremental",
        target_slot="next",
        source_ids=("knowledge_general_ai",),
    )
    checkpoint = BuildCheckpoint(
        source_id="knowledge_general_ai",
        build_id="build_001",
        group_id="general",
        namespace="knowledge",
        user_id=None,
        scan_checkpoint={
            "mode": "file_tree",
            "last_seen_file": "groups/general/knowledge/raw/ai/report.txt",
            "last_seen_mtime": 123,
            "last_seen_hash": "sha256:abc",
            "scanned_file_count": 1,
        },
        doc_local_progress={"section_index": 1, "paragraph_index": 0, "chunk_index": 0},
        pipeline_progress={"stage": "chunked", "parsed_docs": 1, "chunked_docs": 1},
    )

    store.append_build(request, status="running")
    store.write_checkpoint(checkpoint)

    lines = [json.loads(line) for line in (local_tmp_path / "build_registry.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    persisted = json.loads((local_tmp_path / "checkpoints.json").read_text(encoding="utf-8"))

    assert lines[0]["status"] == "running"
    assert persisted["knowledge_general_ai"]["pipeline_progress"]["stage"] == "chunked"
    assert persisted["knowledge_general_ai"]["scan_checkpoint"]["last_seen_file"].endswith("report.txt")


def test_work_queue_tracks_build_and_document_rows(local_tmp_path: Path) -> None:
    queue = WorkQueue(local_tmp_path / "work_queue.sqlite")

    queue.enqueue_build(
        build_id="build_001",
        namespace="knowledge",
        group_id="general",
        user_id=None,
        mode="full",
    )
    queue.enqueue_document(
        build_id="build_001",
        doc_id="doc_001",
        source_path="groups/general/knowledge/raw/ai/report.txt",
        stage="chunking",
    )

    import sqlite3

    with sqlite3.connect(local_tmp_path / "work_queue.sqlite") as conn:
        build_row = conn.execute("SELECT mode, status FROM build_queue WHERE build_id = ?", ("build_001",)).fetchone()
        doc_row = conn.execute("SELECT stage, status FROM document_queue WHERE doc_id = ?", ("doc_001",)).fetchone()

    assert build_row == ("full", "pending")
    assert doc_row == ("chunking", "pending")


def test_memory_adapter_and_workflow_adapter_keep_user_group_boundary(local_tmp_path: Path) -> None:
    memory_source = MemorySourceAdapter().build_source_document(
        source_id="domain_case_u1",
        group_id="law",
        user_id="u1",
        source_kind="domain_case",
        source_path="groups/law/users/u1/memory/domain_case/domain_cases.jsonl",
        content="Breach liability depends on foreseeability.",
    )
    parsed = SimpleTextParser().parse("doc_case_1", memory_source)
    normalized = DocumentNormalizer().normalize(parsed)
    chunks = TextChunker().chunk(normalized)

    lexical = LexicalIndex(local_tmp_path / "lexical" / "term_postings.sqlite", local_tmp_path / "lexical" / "globals.json")
    lexical.rebuild(chunks)
    adapter = WorkflowRetrievalAdapter(local_tmp_path / "lexical" / "term_postings.sqlite", local_tmp_path / "lexical" / "globals.json")

    hits = adapter.retrieve("foreseeability", top_k=3)
    miss = adapter.retrieve("angioplasty", top_k=3)

    assert memory_source.user_id == "u1"
    assert hits
    assert miss == []


def test_repo_knowledge_retriever_reads_general_and_law_sources(local_tmp_path: Path) -> None:
    backend_dir = local_tmp_path / "backend"
    general_file = backend_dir / "storage" / "groups" / "general" / "knowledge" / "raw" / "ai" / "agent_report.txt"
    law_file = backend_dir / "storage" / "groups" / "law" / "knowledge" / "raw" / "cn" / "trial.md"
    general_file.parent.mkdir(parents=True, exist_ok=True)
    law_file.parent.mkdir(parents=True, exist_ok=True)
    general_file.write_text("Agent retrieval planning and orchestration.", encoding="utf-8")
    law_file.write_text("# 劳动合同法\n\n试用期依据来自劳动合同法第19条。", encoding="utf-8")

    retriever = RepoKnowledgeRetriever(backend_dir=backend_dir)

    general_hits = retriever.retrieve("orchestration", top_k=3)
    law_hits = retriever.retrieve("试用期依据", top_k=3)

    assert any("storage/groups/general/knowledge/raw/ai" in item.source_path for item in general_hits.bm25_evidences)
    assert any("storage/groups/law/knowledge/raw/cn" in item.source_path for item in law_hits.bm25_evidences)


def test_simple_vector_index_recalls_semantic_overlap(local_tmp_path: Path) -> None:
    source = KnowledgeSourceAdapter().build_source_document(
        source_id="knowledge_general_finance",
        group_id="general",
        source_path="groups/general/knowledge/raw/finance/report.txt",
        content="Revenue growth and margin expansion.",
        file_type="txt",
    )
    parsed = SimpleTextParser().parse("doc_finance_1", source)
    normalized = DocumentNormalizer().normalize(parsed)
    chunks = TextChunker().chunk(normalized)

    vector = SimpleVectorIndex(local_tmp_path / "vector" / "index.sqlite")
    vector.rebuild(chunks)

    hits = vector.query("revenue margin", top_k=3)
    miss = vector.query("angioplasty stent", top_k=3)

    assert hits
    assert miss == []


def test_repo_knowledge_index_manager_rebuilds_and_switches_slots(local_tmp_path: Path) -> None:
    backend_dir = local_tmp_path / "backend"
    source_file = backend_dir / "storage" / "groups" / "general" / "knowledge" / "raw" / "ai" / "agent_report.txt"
    source_file.parent.mkdir(parents=True, exist_ok=True)
    source_file.write_text("Agent retrieval planning and orchestration.", encoding="utf-8")

    manager = RepoKnowledgeIndexManager(backend_dir=backend_dir)
    manager.rebuild_index()

    status = manager.status()
    manifest_path = backend_dir / "storage" / "groups" / "general" / "registries" / "index_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert status.ready is True
    assert status.indexed_files >= 1
    assert status.vector_ready is True
    assert status.bm25_ready is True
    assert manifest["active_slot"] in {"current", "next"}


def test_parser_preserves_pdf_page_locators(local_tmp_path: Path) -> None:
    source = KnowledgeSourceAdapter().build_source_document(
        source_id="knowledge_general_pdf",
        group_id="general",
        source_path="groups/general/knowledge/raw/ai/report.pdf",
        content="第一页摘要段落。\n\n第二段。 \f 第二页分析段落。",
        file_type="pdf",
        metadata={"title": "PDF report"},
        revision="rev-pdf",
    )

    parsed = SimpleTextParser().parse("doc_pdf_1", source)

    assert parsed.sections
    assert parsed.sections[0]["locator"].get("page_no") == 1
    assert any(section["locator"].get("page_no") == 2 for section in parsed.sections)


def test_parser_keeps_excel_as_structured_summary_blocks(local_tmp_path: Path) -> None:
    workbook_summary = {
        "type": "xlsx_summary",
        "file": "metrics.xlsx",
        "sheets": [
            {
                "sheet_name": "metrics",
                "headers": ["month", "revenue"],
                "row_count": 2,
                "preview_rows": [["Jan", "100"], ["Feb", "120"]],
            }
        ],
    }
    source = KnowledgeSourceAdapter().build_source_document(
        source_id="knowledge_general_excel",
        group_id="general",
        source_path="groups/general/knowledge/raw/finance/metrics.xlsx",
        content=json.dumps(workbook_summary, ensure_ascii=False),
        file_type="xlsx",
        metadata={"title": "Metrics workbook"},
        revision="rev-xlsx",
    )

    parsed = SimpleTextParser().parse("doc_xlsx_1", source)
    normalized = DocumentNormalizer().normalize(parsed)
    chunks = TextChunker().chunk(normalized)

    assert parsed.sections
    assert parsed.sections[0]["locator"].get("sheet_name") == "metrics"
    assert chunks
    assert all(chunk.metadata.get("structured_only") is True for chunk in chunks)


def test_memory_hybrid_retriever_recalls_domain_case_and_daily_log(local_tmp_path: Path) -> None:
    from datetime import datetime

    from context.models import MemoryEntry
    from retrieval_infra.query.memory_hybrid_retriever import MemoryHybridRetriever

    storage_root = local_tmp_path / "storage"
    retriever = MemoryHybridRetriever(storage_root)
    entries = [
        MemoryEntry(
            content="今天继续讨论 breach liability 与 damages 的关系。",
            source="groups/law/users/u1/memory/daily_log/2026-05-30.jsonl",
            group_id="law",
            user_id="u1",
            timestamp=datetime.now(),
            memory_type="daily_log",
            metadata={"id": "mem_daily_1"},
        ),
        MemoryEntry(
            content="该案例强调 breach liability 的 foreseeability 分析。",
            source="groups/law/users/u1/memory/domain_case/domain_cases.jsonl",
            group_id="law",
            user_id="u1",
            timestamp=datetime.now(),
            memory_type="domain_case",
            title="Breach liability case",
            metadata={"id": "mem_case_1"},
        ),
    ]

    hits = retriever.retrieve(
        group_id="law",
        user_id="u1",
        query="breach liability foreseeability",
        memory_entries=entries,
        top_k=5,
    )

    assert hits
    assert {item.memory_type for item in hits} == {"daily_log", "domain_case"}
