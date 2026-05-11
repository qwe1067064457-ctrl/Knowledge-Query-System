from __future__ import annotations

import json
import sys
import uuid
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from legal_crawler.law_kb_builder import build_law_knowledge_base


TEST_TMP_ROOT = Path(__file__).resolve().parent / ".test_tmp"


@pytest.fixture
def workspace() -> Path:
    path = TEST_TMP_ROOT / f"case_{uuid.uuid4().hex}"
    path.mkdir(parents=True, exist_ok=False)
    return path


def write_doc(path: Path, title: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"# {title}\n\nBody.\n", encoding="utf-8")


def test_build_law_knowledge_base_copies_documents_and_writes_indexes(workspace: Path) -> None:
    backend_dir = workspace / "backend"
    source_dir = backend_dir / "storage" / "knowledge" / "legal_corpus" / "documents_by_category"
    write_doc(source_dir / "agriculture" / "00001_doc.md", "Agriculture")
    write_doc(source_dir / "tax" / "00002_doc.md", "Tax")

    summary = build_law_knowledge_base(backend_dir=backend_dir, source_dir=source_dir)

    assert summary.copied == 2
    assert (backend_dir / "knowledge" / "groups" / "law" / "README.md").exists()
    assert (backend_dir / "knowledge" / "groups" / "law" / "documents" / "index.md").exists()
    assert (backend_dir / "knowledge" / "groups" / "law" / "documents" / "us" / "ecfr" / "index.md").exists()
    assert (backend_dir / "knowledge" / "groups" / "law" / "documents" / "cn" / "index.md").exists()
    assert (
        backend_dir
        / "knowledge"
        / "groups"
        / "law"
        / "documents"
        / "us"
        / "ecfr"
        / "agriculture"
        / "00001_doc.md"
    ).exists()
    assert (
        backend_dir
        / "knowledge"
        / "groups"
        / "law"
        / "documents"
        / "us"
        / "ecfr"
        / "tax"
        / "00002_doc.md"
    ).exists()


def test_build_law_knowledge_base_writes_manifest_and_minimal_storage(workspace: Path) -> None:
    backend_dir = workspace / "backend"
    source_dir = backend_dir / "storage" / "knowledge" / "legal_corpus" / "documents_by_category"
    write_doc(source_dir / "health" / "00001_doc.md", "Health")

    summary = build_law_knowledge_base(backend_dir=backend_dir, source_dir=source_dir)

    manifest = json.loads(summary.manifest_path.read_text(encoding="utf-8"))
    assert manifest["group_id"] == "law"
    assert manifest["total_documents"] == 1
    assert manifest["categories"]["health"]["count"] == 1
    assert (backend_dir / "storage" / "groups" / "law" / "meta.json").exists()
    assert (backend_dir / "storage" / "groups" / "law" / "shared" / "domain_cases" / "index.json").exists()


def test_build_law_knowledge_base_rejects_missing_source(workspace: Path) -> None:
    with pytest.raises(FileNotFoundError):
        build_law_knowledge_base(backend_dir=workspace / "backend", source_dir=workspace / "missing")
