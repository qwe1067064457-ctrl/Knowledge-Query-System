from __future__ import annotations

import json
import sys
import uuid
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import api.groups as groups_api
from group_management import GroupManagementService


def _make_temp_backend_dir() -> Path:
    temp_root = ROOT / "backend" / ".test_tmp" / "groups_api_registry_recovery"
    temp_root.mkdir(parents=True, exist_ok=True)
    directory = temp_root / f"case_{uuid.uuid4().hex}"
    directory.mkdir(parents=True, exist_ok=False)
    return directory


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _seed_group_meta(backend_dir: Path, *, group_id: str, name: str, status: str = "active") -> None:
    _write_json(
        backend_dir / "storage" / "groups" / group_id / "meta.json",
        {
            "id": group_id,
            "name": name,
            "description": f"{name} description",
            "status": status,
            "default_agent_id": "default",
            "created_by": "seed",
            "created_at": "2026-07-01T00:00:00+00:00",
            "updated_at": "2026-07-01T00:00:00+00:00",
            "knowledge": {
                "storage_root": f"storage/groups/{group_id}/knowledge",
                "raw": f"storage/groups/{group_id}/knowledge/raw",
                "indexes": f"storage/groups/{group_id}/knowledge/indexes",
            },
            "memory_policy": {},
            "metadata": {"source": "seed"},
        },
    )


def _build_client(backend_dir: Path) -> TestClient:
    service = GroupManagementService(backend_dir)
    if hasattr(groups_api._service, "cache_clear"):
        groups_api._service.cache_clear()
    groups_api._service = lambda: service
    app = FastAPI()
    app.include_router(groups_api.router, prefix="/api")
    return TestClient(app)


def test_groups_api_recovers_registry_from_group_meta_files() -> None:
    backend_dir = _make_temp_backend_dir()
    _seed_group_meta(backend_dir, group_id="general", name="General")
    _seed_group_meta(backend_dir, group_id="law", name="Law")
    _seed_group_meta(backend_dir, group_id="medicine", name="Medicine")

    client = _build_client(backend_dir)
    response = client.get("/api/groups")

    assert response.status_code == 200
    payload = response.json()
    assert [item["id"] for item in payload] == ["general", "law", "medicine"]
    registry_path = backend_dir / "storage" / "groups" / "registry.json"
    assert registry_path.exists()
    registry_payload = json.loads(registry_path.read_text(encoding="utf-8"))
    assert [item["id"] for item in registry_payload["items"]] == ["general", "law", "medicine"]


def test_groups_api_ignores_invalid_group_meta_and_filters_archived_by_default() -> None:
    backend_dir = _make_temp_backend_dir()
    _seed_group_meta(backend_dir, group_id="general", name="General")
    _seed_group_meta(backend_dir, group_id="law", name="Law", status="archived")
    broken_meta_path = backend_dir / "storage" / "groups" / "broken" / "meta.json"
    broken_meta_path.parent.mkdir(parents=True, exist_ok=True)
    broken_meta_path.write_text("{not json}", encoding="utf-8")

    client = _build_client(backend_dir)
    default_response = client.get("/api/groups")
    archived_response = client.get("/api/groups", params={"include_archived": True})

    assert default_response.status_code == 200
    assert archived_response.status_code == 200
    assert [item["id"] for item in default_response.json()] == ["general"]
    assert [item["id"] for item in archived_response.json()] == ["general", "law"]
