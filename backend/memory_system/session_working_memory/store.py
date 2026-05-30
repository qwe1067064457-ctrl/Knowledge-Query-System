from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from memory_system.session_working_memory.models import (
    SessionWorkingMemory,
    WorkingMemoryEntry,
    WorkingMemoryHead,
)
from memory_system.session_working_memory.retention import SessionWorkingMemoryRetention


class SessionWorkingMemoryStore:
    def __init__(self, base_storage_path: Path) -> None:
        self.base_storage_path = Path(base_storage_path)
        self.retention = SessionWorkingMemoryRetention()

    def get_paths(
        self,
        *,
        group_id: str,
        agent_id: str,
        session_id: str,
        user_id: str | None = None,
    ) -> tuple[Path, Path]:
        if not user_id:
            raise ValueError("user_id is required for session working memory paths")
        session_dir = self.base_storage_path / "groups" / group_id / "users" / user_id / "sessions"
        session_dir.mkdir(parents=True, exist_ok=True)
        return (
            session_dir / f"{session_id}.working_memory.jsonl",
            session_dir / f"{session_id}.working_memory.head.json",
        )

    def load(
        self,
        *,
        group_id: str,
        agent_id: str,
        session_id: str,
        user_id: str | None = None,
    ) -> SessionWorkingMemory | None:
        jsonl_path, head_path = self.get_paths(group_id=group_id, agent_id=agent_id, session_id=session_id, user_id=user_id)
        if jsonl_path.exists() or head_path.exists():
            entries = self._read_jsonl(jsonl_path)
            head = WorkingMemoryHead.from_dict(self._read_json(head_path, {}))
            return SessionWorkingMemory(entries=entries, head=head)
        return None

    def save(
        self,
        *,
        group_id: str,
        agent_id: str,
        session_id: str,
        user_id: str | None = None,
        memory: SessionWorkingMemory | dict[str, Any],
    ) -> SessionWorkingMemory:
        normalized = (
            memory
            if isinstance(memory, SessionWorkingMemory)
            else SessionWorkingMemory.from_dict(memory)
        )
        normalized = self.retention.merge(SessionWorkingMemory(), normalized.entries)
        jsonl_path, head_path = self.get_paths(group_id=group_id, agent_id=agent_id, session_id=session_id, user_id=user_id)
        self._write_jsonl(jsonl_path, normalized.entries)
        self._write_json(head_path, normalized.head.to_dict())
        return normalized

    def append_entries(
        self,
        *,
        group_id: str,
        agent_id: str,
        session_id: str,
        user_id: str | None = None,
        entries: list[WorkingMemoryEntry],
    ) -> SessionWorkingMemory:
        current = self.load(group_id=group_id, agent_id=agent_id, session_id=session_id, user_id=user_id)
        merged = self.retention.merge(current, entries)
        jsonl_path, head_path = self.get_paths(group_id=group_id, agent_id=agent_id, session_id=session_id, user_id=user_id)
        self._write_jsonl(jsonl_path, merged.entries)
        self._write_json(head_path, merged.head.to_dict())
        return merged

    def _read_jsonl(self, path: Path) -> list[WorkingMemoryEntry]:
        rows: list[WorkingMemoryEntry] = []
        if not path.exists():
            return rows
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                try:
                    rows.append(WorkingMemoryEntry.from_dict(json.loads(line)))
                except json.JSONDecodeError:
                    continue
        return rows

    def _write_jsonl(self, path: Path, entries: list[WorkingMemoryEntry]) -> None:
        with path.open("w", encoding="utf-8") as handle:
            for entry in entries:
                handle.write(json.dumps(entry.to_dict(), ensure_ascii=False) + "\n")

    def _read_json(self, path: Path, default: Any) -> Any:
        if not path.exists():
            return default
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return default

    def _write_json(self, path: Path, payload: Any) -> None:
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
