from __future__ import annotations

import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.runtime_memory import router
from graph.agent import agent_manager
from memory_system.memory_service import MemorySystem


def _build_test_client(memory_system: MemorySystem) -> TestClient:
    app = FastAPI()
    app.include_router(router, prefix="/api")
    agent_manager.memory_system = memory_system
    return TestClient(app)


def _make_temp_dir() -> Path:
    temp_root = ROOT / "backend" / ".test_tmp" / "runtime_memory_api"
    temp_root.mkdir(parents=True, exist_ok=True)
    directory = temp_root / f"case_{uuid.uuid4().hex}"
    directory.mkdir(parents=True, exist_ok=False)
    return directory


def test_runtime_memory_core_api_returns_default_user_memory() -> None:
    tmp_path = _make_temp_dir()
    memory_system = MemorySystem(tmp_path / "storage")
    memory_system.write_core_memory(
        user_id="default",
        group_id=None,
        scope="user_global",
        content="我偏好中文输出。",
        title="输出偏好",
        tags=["preference"],
    )
    memory_system.write_core_memory(
        user_id="default",
        group_id="general",
        scope="user_group",
        content="法律组里优先引用法条依据。",
        title="法律回答偏好",
        tags=["law"],
    )

    client = _build_test_client(memory_system)
    response = client.get("/api/runtime/memory/core")

    assert response.status_code == 200
    payload = response.json()
    assert payload["user_id"] == "default"
    assert payload["group_id"] == "general"
    assert payload["counts"] == {
        "user_global": 1,
        "user_group": 1,
        "total": 2,
    }
    assert payload["storage"]["user_global_core"] == "users/default/memory/core/global.json"
    assert payload["storage"]["user_group_core"] == "groups/general/users/default/memory/core/group.json"
    assert {item["scope"] for item in payload["items"]} == {"user_global", "user_group"}
    assert any(item["content"] == "我偏好中文输出。" for item in payload["items"])
    assert any(item["content"] == "法律组里优先引用法条依据。" for item in payload["items"])


def test_runtime_memory_overview_api_reports_counts_and_empty_state() -> None:
    tmp_path = _make_temp_dir()
    memory_system = MemorySystem(tmp_path / "storage")
    memory_system.write_core_memory(
        user_id="default",
        group_id=None,
        scope="user_global",
        content="长期记住：默认使用中文。",
        title="语言偏好",
    )

    client = _build_test_client(memory_system)
    response = client.get("/api/runtime/memory/overview", params={"group_id": "law"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["user_id"] == "default"
    assert payload["group_id"] == "law"
    assert payload["counts"]["core_total"] == 1
    assert payload["counts"]["user_global_core"] == 1
    assert payload["counts"]["user_group_core"] == 0
    assert payload["counts"]["daily_log_files"] == 0
    assert payload["counts"]["daily_log_entries"] == 0
    assert payload["counts"]["domain_case_entries"] == 0
    assert payload["exists"]["user_global_core"] is True
    assert payload["exists"]["user_group_core"] is False


def test_runtime_memory_api_returns_503_when_memory_system_is_missing() -> None:
    app = FastAPI()
    app.include_router(router, prefix="/api")
    agent_manager.memory_system = None
    client = TestClient(app)

    response = client.get("/api/runtime/memory/core")

    assert response.status_code == 503
    assert response.json()["detail"] == "Memory system is not initialized"
