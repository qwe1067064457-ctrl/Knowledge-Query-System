from __future__ import annotations

import json
import sys
import shutil
import zipfile
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
from retrieval_infra.query.reranker import LocalCrossEncoderReranker
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
    switched = store.activate(
        "knowledge",
        current_build_id="build_001",
        current_snapshot_id="snap_001",
        previous_snapshot_id="snap_000",
    )
    rolled_back = store.rollback(
        "knowledge",
        current_build_id="build_rollback",
        current_snapshot_id="snap_rollback",
        previous_snapshot_id="snap_001",
    )

    assert initial.current_build_id is None
    assert switched.current_build_id == "build_001"
    assert switched.current_snapshot_id == "snap_001"
    assert switched.previous_snapshot_id == "snap_000"
    assert rolled_back.current_build_id == "build_rollback"
    assert rolled_back.current_snapshot_id == "snap_rollback"
    assert rolled_back.previous_snapshot_id == "snap_001"


def test_state_store_persists_build_and_checkpoint(local_tmp_path: Path) -> None:
    store = StateStore(registries_dir=local_tmp_path / "registries")
    request = BuildRequest(
        build_id="build_001",
        group_id="general",
        namespace="knowledge",
        mode="incremental",
        source_ids=("knowledge_general_ai",),
        source_fingerprint="fp_001",
        candidate_dir=str(local_tmp_path / "candidate" / "build_001"),
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

    lines = [json.loads(line) for line in (local_tmp_path / "registries" / "history" / "build_registry.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    persisted_scan = store.load_scan_checkpoints()
    persisted_docs = store.load_document_checkpoints()

    assert lines[0]["status"] == "running"
    assert persisted_scan["build_001"]["last_seen_file"].endswith("report.txt")
    assert persisted_docs["build_001::knowledge_general_ai"]["stage"] == "chunked"


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
    group_root = backend_dir / "storage" / "groups" / "general"
    manifest_path = group_root / "registries" / "index_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert status.ready is True
    assert status.indexed_files >= 1
    assert status.vector_ready is True
    assert status.bm25_ready is True
    assert manifest["current_build_id"].startswith("b_gen_")
    assert manifest["current_snapshot_id"].startswith("s_b_gen_")
    assert "active_slot" not in manifest
    assert (group_root / "knowledge" / "indexes" / "builds" / "running" / manifest["current_build_id"]).exists()
    assert (group_root / "knowledge" / "indexes" / "builds" / "latest" / manifest["current_build_id"]).exists()
    assert (group_root / "registries" / "history" / "source_registry.jsonl").exists()
    assert (group_root / "registries" / "history" / "build_history.jsonl").exists()
    assert (group_root / "registries" / "history" / "validation_history.jsonl").exists()
    assert (group_root / "registries" / "recovery" / "scan_checkpoints.sqlite").exists()
    assert (group_root / "registries" / "recovery" / "document_checkpoints.sqlite").exists()
    assert (group_root / "registries" / "recovery" / "index_checkpoints.sqlite").exists()
    assert (group_root / "registries" / "recovery" / "activation_checkpoints.sqlite").exists()


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
    assert all(chunk.metadata.get("analysis_available") is True for chunk in chunks)


def test_repo_knowledge_retriever_returns_table_hits_with_analysis_flag(local_tmp_path: Path) -> None:
    backend_dir = local_tmp_path / "backend"
    workbook_path = backend_dir / "storage" / "groups" / "general" / "knowledge" / "raw" / "finance" / "metrics.xlsx"
    workbook_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(workbook_path, "w") as archive:
        archive.writestr(
            "xl/workbook.xml",
            """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"
 xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheets>
    <sheet name="monthly_revenue" sheetId="1" r:id="rId1"/>
  </sheets>
</workbook>""",
        )
        archive.writestr(
            "xl/_rels/workbook.xml.rels",
            """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
</Relationships>""",
        )
        archive.writestr(
            "xl/worksheets/sheet1.xml",
            """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <sheetData>
    <row r="1">
      <c r="A1" t="inlineStr"><is><t>date</t></is></c>
      <c r="B1" t="inlineStr"><is><t>product</t></is></c>
      <c r="C1" t="inlineStr"><is><t>region</t></is></c>
      <c r="D1" t="inlineStr"><is><t>revenue</t></is></c>
    </row>
    <row r="2">
      <c r="A2" t="inlineStr"><is><t>2025-01</t></is></c>
      <c r="B2" t="inlineStr"><is><t>A</t></is></c>
      <c r="C2" t="inlineStr"><is><t>华东</t></is></c>
      <c r="D2" t="inlineStr"><is><t>183200</t></is></c>
    </row>
    <row r="3">
      <c r="A3" t="inlineStr"><is><t>2025-02</t></is></c>
      <c r="B3" t="inlineStr"><is><t>B</t></is></c>
      <c r="C3" t="inlineStr"><is><t>华南</t></is></c>
      <c r="D3" t="inlineStr"><is><t>97500</t></is></c>
    </row>
  </sheetData>
</worksheet>""",
        )

    retriever = RepoKnowledgeRetriever(backend_dir=backend_dir)
    result = retriever.retrieve("哪个 region 的 revenue 更高", top_k=5)

    assert result.table_hits
    assert any(item.metadata.get("analysis_available") is True for item in result.table_hits)
    assert any(item.metadata.get("structured_only") is True for item in result.table_hits)


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


def test_local_cross_encoder_reranker_falls_back_to_heuristic_when_no_model() -> None:
    from knowledge_retrieval.types import Evidence

    reranker = LocalCrossEncoderReranker(model_ref="definitely_missing_model")
    ranked = reranker.rerank(
        "breach liability",
        [
            Evidence(source_path="a.md", source_type="md", locator="p1", snippet="breach liability analysis", channel="bm25", score=0.2),
            Evidence(source_path="b.md", source_type="md", locator="p2", snippet="cardiology", channel="bm25", score=0.1),
        ],
        top_k=2,
    )

    assert reranker.active_backend == "heuristic"
    assert ranked[0].snippet == "breach liability analysis"


def test_local_cross_encoder_reranker_prefers_local_model_backend(monkeypatch: pytest.MonkeyPatch, local_tmp_path: Path) -> None:
    from knowledge_retrieval.types import Evidence

    model_dir = local_tmp_path / "fake_reranker"
    model_dir.mkdir(parents=True, exist_ok=True)
    reranker = LocalCrossEncoderReranker(model_ref=str(model_dir))

    monkeypatch.setattr(reranker, "_discover_local_model", lambda: model_dir)
    monkeypatch.setattr(
        reranker,
        "_load_local_cross_encoder",
        lambda _model_path: (lambda query, evidences: [0.1 if "cardiology" in item.snippet else 0.9 for item in evidences]),
    )

    ranked = reranker.rerank(
        "breach liability",
        [
            Evidence(source_path="a.md", source_type="md", locator="p1", snippet="cardiology note", channel="vector", score=0.8),
            Evidence(source_path="b.md", source_type="md", locator="p2", snippet="breach liability analysis", channel="vector", score=0.1),
        ],
        top_k=2,
    )

    assert reranker.active_backend == str(model_dir)
    assert ranked[0].snippet == "breach liability analysis"
