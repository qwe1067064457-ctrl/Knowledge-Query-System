from __future__ import annotations

import shutil
import sys
import time
import uuid
from contextlib import contextmanager
import json
from pathlib import Path
from typing import Any, Dict, Iterator


ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from context.context_manager import ContextManager
from context.dataclasses import TranscriptEntry
from context.session_manager import SessionManager
from memory_system import MemorySystem


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


def make_context_manager(workspace: Path) -> ContextManager:
    sessions = make_session_manager(workspace)
    memory = make_memory_system(workspace)
    return ContextManager(sessions, memory)


def write_group_meta(workspace: Path, group_id: str, memory_policy: Dict[str, Any]) -> Path:
    path = workspace / "storage" / "groups" / group_id / "meta.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"memory_policy": memory_policy}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return path


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
