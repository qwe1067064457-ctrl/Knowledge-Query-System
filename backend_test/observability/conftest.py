from __future__ import annotations

import shutil
import sys
import time
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

import pytest

ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from context.assembly.context_manager import ContextManager
from context.models import TranscriptEntry
from context.session.session_manager import SessionManager
from memory_system import MemorySystem


@pytest.fixture
def workspace() -> Path:
    with temp_workspace() as path:
        yield path


TEST_TMP_ROOT = Path(__file__).resolve().parent / ".test_tmp"


@contextmanager
def temp_workspace() -> Iterator[Path]:
    TEST_TMP_ROOT.mkdir(exist_ok=True)
    path = TEST_TMP_ROOT / f"case_{uuid.uuid4().hex}"
    path.mkdir(parents=True, exist_ok=False)
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


def make_session_manager(workspace: Path) -> SessionManager:
    return SessionManager(workspace / "storage")


def make_memory_system(workspace: Path) -> MemorySystem:
    return MemorySystem(workspace / "storage")


def make_context_manager(
    workspace: Path,
    sessions: SessionManager | None = None,
    memory: MemorySystem | None = None,
) -> ContextManager:
    sessions = sessions or make_session_manager(workspace)
    memory = memory or make_memory_system(workspace)
    return ContextManager(sessions, memory)


def make_entry(
    session_id: str,
    group_id: str,
    role: str,
    content: str,
    *,
    entry_type: str = "normal",
    token_count: int | None = None,
) -> TranscriptEntry:
    return TranscriptEntry(
        id=f"entry_{time.time_ns()}_{uuid.uuid4().hex[:6]}",
        session_id=session_id,
        group_id=group_id,
        timestamp=int(time.time() * 1000),
        role=role,
        entry_type=entry_type,
        content=content,
        token_count=token_count,
    )


def pytest_sessionfinish(session, exitstatus):  # type: ignore[no-untyped-def]
    try:
        shutil.rmtree(TEST_TMP_ROOT, ignore_errors=True)
    except OSError:
        pass
