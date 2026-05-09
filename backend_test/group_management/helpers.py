from __future__ import annotations

import json
import shutil
import sys
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from fastapi import FastAPI
from fastapi.testclient import TestClient


ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from backend.group_management import ConflictError, GroupManagementService, NotFoundError, ValidationError


TEST_TMP_ROOT = Path(__file__).resolve().parent / ".test_tmp"

DEFAULT_MEMORY_POLICY = {
    "memory_policy": {
        "enabled_memory_types": ["core", "daily_log", "domain_case"],
        "core": {
            "explicit_markers": ["always", "default"],
            "group_scope_keywords": ["law", "contract"],
            "min_candidate_length": 3,
            "max_candidate_length": 120,
        },
        "daily_log": {"checkpoint_enabled": True},
        "domain_case": {
            "completion_markers": ["done", "conclusion"],
            "structural_markers": ["problem", "analysis", "conclusion"],
            "case_markers": ["case"],
        },
    }
}


@contextmanager
def temp_backend_dir(*, with_policy: bool = True) -> Iterator[Path]:
    TEST_TMP_ROOT.mkdir(parents=True, exist_ok=True)
    backend_dir = TEST_TMP_ROOT / f"case_{uuid.uuid4().hex}"
    backend_dir.mkdir(parents=True, exist_ok=False)
    if with_policy:
        policy_path = backend_dir / "memory_system" / "policy.default.json"
        write_json(policy_path, DEFAULT_MEMORY_POLICY)
    try:
        yield backend_dir
    finally:
        shutil.rmtree(backend_dir, ignore_errors=True)


def make_service(backend_dir: Path) -> GroupManagementService:
    return GroupManagementService(backend_dir)


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def seed_user(service: GroupManagementService, user_id: str = "u1") -> dict:
    return service.create_user(user_id=user_id, display_name=f"User {user_id}")


def make_api_client(service: GroupManagementService) -> TestClient:
    import api.groups as groups_api
    import api.users as users_api

    groups_api.ConflictError = ConflictError
    groups_api.NotFoundError = NotFoundError
    groups_api.ValidationError = ValidationError
    users_api.ConflictError = ConflictError
    users_api.NotFoundError = NotFoundError
    users_api.ValidationError = ValidationError

    groups_cache_clear = getattr(groups_api._service, "cache_clear", None)
    users_cache_clear = getattr(users_api._service, "cache_clear", None)
    if groups_cache_clear:
        groups_cache_clear()
    if users_cache_clear:
        users_cache_clear()
    groups_api._service = lambda: service
    users_api._service = lambda: service

    app = FastAPI()
    app.include_router(users_api.router, prefix="/api")
    app.include_router(groups_api.router, prefix="/api")
    return TestClient(app)
