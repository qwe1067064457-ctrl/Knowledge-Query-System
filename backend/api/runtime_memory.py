from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query

from context.models import MemoryEntry
from graph.agent import agent_manager
from memory_system.memory_service import MemorySystem

router = APIRouter()


def _get_memory_system() -> MemorySystem:
    memory_system = agent_manager.memory_system
    if memory_system is None:
        raise HTTPException(status_code=503, detail="Memory system is not initialized")
    return memory_system


def _serialize_memory_entry(entry: MemoryEntry) -> dict[str, Any]:
    """Expose stable memory fields without leaking internal Python objects."""
    return {
        "content": entry.content,
        "source": entry.source,
        "group_id": entry.group_id,
        "timestamp": entry.timestamp.isoformat(),
        "score": entry.score,
        "scope": entry.scope,
        "memory_type": entry.memory_type,
        "user_id": entry.user_id,
        "title": entry.title,
        "subject": entry.subject,
        "tags": list(entry.tags or []),
        "source_session_id": entry.source_session_id,
        "anchor_spans": list(entry.anchor_spans or []),
        "confidence": entry.confidence,
        "metadata": dict(entry.metadata or {}),
    }


def _count_jsonl_rows(path: Path) -> int:
    if not path.exists():
        return 0
    count = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            count += 1
    return count


def _build_storage_paths(memory_system: MemorySystem, *, user_id: str, group_id: str) -> dict[str, str]:
    global_core_path = memory_system._core_file(user_id, "user_global")
    group_core_path = memory_system._core_file(user_id, "user_group", group_id=group_id)
    daily_log_dir = memory_system._daily_log_dir(user_id, group_id)
    domain_case_file = memory_system._domain_cases_file(group_id, user_id)
    return {
        "user_global_core": global_core_path.relative_to(memory_system.base_storage_path).as_posix(),
        "user_group_core": group_core_path.relative_to(memory_system.base_storage_path).as_posix(),
        "daily_log_dir": daily_log_dir.relative_to(memory_system.base_storage_path).as_posix(),
        "domain_case_file": domain_case_file.relative_to(memory_system.base_storage_path).as_posix(),
    }


@router.get("/runtime/memory/core")
async def get_runtime_core_memory(
    user_id: str = Query("default", min_length=1),
    group_id: str = Query("general", min_length=1),
) -> dict[str, Any]:
    memory_system = _get_memory_system()
    entries = memory_system.get_core_memories(user_id=user_id, group_id=group_id)
    scope_counts = {
        "user_global": sum(1 for item in entries if item.scope == "user_global"),
        "user_group": sum(1 for item in entries if item.scope == "user_group"),
        "total": len(entries),
    }
    return {
        "user_id": user_id,
        "group_id": group_id,
        "storage": _build_storage_paths(memory_system, user_id=user_id, group_id=group_id),
        "counts": scope_counts,
        "items": [_serialize_memory_entry(item) for item in entries],
    }


@router.get("/runtime/memory/overview")
async def get_runtime_memory_overview(
    user_id: str = Query("default", min_length=1),
    group_id: str = Query("general", min_length=1),
) -> dict[str, Any]:
    memory_system = _get_memory_system()
    core_entries = memory_system.get_core_memories(user_id=user_id, group_id=group_id)
    global_core_path = memory_system._core_file(user_id, "user_global")
    group_core_path = memory_system._core_file(user_id, "user_group", group_id=group_id)
    daily_log_dir = memory_system._daily_log_dir(user_id, group_id)
    domain_case_file = memory_system._domain_cases_file(group_id, user_id)

    daily_log_files = sorted(daily_log_dir.glob("*.jsonl"))
    return {
        "user_id": user_id,
        "group_id": group_id,
        "storage": _build_storage_paths(memory_system, user_id=user_id, group_id=group_id),
        "counts": {
            "core_total": len(core_entries),
            "user_global_core": sum(1 for item in core_entries if item.scope == "user_global"),
            "user_group_core": sum(1 for item in core_entries if item.scope == "user_group"),
            "daily_log_files": len(daily_log_files),
            "daily_log_entries": sum(_count_jsonl_rows(path) for path in daily_log_files),
            "domain_case_entries": _count_jsonl_rows(domain_case_file),
        },
        "exists": {
            "user_global_core": global_core_path.exists(),
            "user_group_core": group_core_path.exists(),
            "daily_log_dir": daily_log_dir.exists(),
            "domain_case_file": domain_case_file.exists(),
        },
    }
