from __future__ import annotations

import sys
import os
import shutil
import time
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Callable

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = REPO_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from context.dataclasses import TranscriptEntry
from context.session_manager import SessionManager


WORKER_ID = os.environ.get("PYTEST_XDIST_WORKER", "main")
TEST_TMP_ROOT = Path(__file__).resolve().parent / ".session_test_tmp" / WORKER_ID


@contextmanager
def _local_temp_dir():
    TEST_TMP_ROOT.mkdir(exist_ok=True)
    temp_dir = TEST_TMP_ROOT / f"case_{uuid.uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=False)
    try:
        yield temp_dir
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def tmp_storage_root() -> Path:
    with _local_temp_dir() as temp_dir:
        yield temp_dir / "storage_root"


@pytest.fixture
def session_manager(tmp_storage_root: Path) -> SessionManager:
    return SessionManager(tmp_storage_root / "storage")


@pytest.fixture
def make_entry() -> Callable[..., TranscriptEntry]:
    def _make_entry(
        *,
        session_id: str,
        group_id: str,
        role: str,
        content: str,
        token_count: int | None = None,
        entry_type: str = "normal",
    ) -> TranscriptEntry:
        return TranscriptEntry(
            id=f"entry_{time.time_ns()}_{uuid.uuid4().hex[:8]}",
            session_id=session_id,
            group_id=group_id,
            timestamp=int(time.time() * 1000),
            role=role,
            entry_type=entry_type,
            content=content,
            token_count=token_count,
        )

    return _make_entry
