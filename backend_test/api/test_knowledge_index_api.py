from __future__ import annotations

import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import api.knowledge_index as knowledge_index_api
from knowledge_retrieval.types import IndexStatus


class _StubKnowledgeIndexer:
    """Keep API tests black-box while controlling indexer behavior."""

    def __init__(self) -> None:
        self.building = False
        self.rebuild_calls: list[str | None] = []

    def status(self, group_id: str | None = None) -> IndexStatus:
        ready = group_id == "law"
        indexed_files = 1 if ready else 3
        return IndexStatus(
            ready=ready or group_id is None,
            building=self.building,
            last_built_at=123.0,
            indexed_files=indexed_files,
            chunk_count=17 if ready else 29,
            vector_ready=True,
            bm25_ready=ready or group_id is None,
        )

    def is_building(self) -> bool:
        return self.building

    def rebuild_index(self, group_id: str | None = None) -> None:
        self.rebuild_calls.append(group_id)

    def list_groups(self) -> list[str]:
        return ["general", "law", "medicine"]

    def count_group_sources(self, group_id: str) -> int:
        return {"general": 12, "law": 34, "medicine": 56}[group_id]


def _build_client(stub_indexer: _StubKnowledgeIndexer) -> TestClient:
    knowledge_index_api.knowledge_indexer = stub_indexer
    if hasattr(knowledge_index_api._group_service, "cache_clear"):
        knowledge_index_api._group_service.cache_clear()
    knowledge_index_api._group_service = lambda: (_ for _ in ()).throw(RuntimeError("registry unavailable"))

    app = FastAPI()
    app.include_router(knowledge_index_api.router, prefix="/api")
    return TestClient(app)


def test_group_index_status_supports_query_and_group_alias() -> None:
    client = _build_client(_StubKnowledgeIndexer())

    query_response = client.get("/api/knowledge/index/status", params={"group_id": "law"})
    alias_response = client.get("/api/groups/law/knowledge/index/status")

    assert query_response.status_code == 200
    assert alias_response.status_code == 200
    assert query_response.json()["group_id"] == "law"
    assert query_response.json()["scope"] == "group"
    assert query_response.json()["source_file_count"] == 34
    assert query_response.json()["chunk_count"] == 17
    assert alias_response.json()["group_id"] == "law"
    assert alias_response.json()["ready"] is True


def test_rebuild_index_accepts_group_specific_requests() -> None:
    stub_indexer = _StubKnowledgeIndexer()
    client = _build_client(stub_indexer)

    response = client.post("/api/groups/medicine/knowledge/index/rebuild")

    assert response.status_code == 200
    assert response.json() == {
        "accepted": True,
        "group_id": "medicine",
        "queued": True,
    }


def test_status_rejects_unknown_group() -> None:
    client = _build_client(_StubKnowledgeIndexer())

    response = client.get("/api/knowledge/index/status", params={"group_id": "unknown"})

    assert response.status_code == 404
    assert response.json()["detail"] == "Group not found: unknown"
