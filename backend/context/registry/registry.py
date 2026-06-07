"""
Registry persistence manager.
"""
from __future__ import annotations

import json
from pathlib import Path

from context.registry.registry_types import ContextRegistry, ContextRegistryEntry
from context.session.session_manager import SessionManager


class ContextRegistryManager:
    def __init__(self, session_manager: SessionManager, *, max_turns: int = 5, max_entries_per_turn: int = 10) -> None:
        self.session_manager = session_manager
        self.max_turns = max_turns
        self.max_entries_per_turn = max_entries_per_turn

    def load_registry(self, session_id: str, tenant_id: str, group_id: str, agent_id: str) -> ContextRegistry:
        path = self._registry_path(group_id, agent_id, session_id)
        if not path.exists():
            return ContextRegistry(tenant_id=tenant_id, group_id=group_id, session_id=session_id)
        data = json.loads(path.read_text(encoding="utf-8"))
        entries = tuple(ContextRegistryEntry.from_dict(item) for item in data.get("entries", ()))
        return ContextRegistry(
            tenant_id=str(data.get("tenant_id", tenant_id)),
            group_id=str(data.get("group_id", group_id)),
            session_id=str(data.get("session_id", session_id)),
            entries=entries,
        )

    def append_entries(
        self,
        session_id: str,
        tenant_id: str,
        group_id: str,
        agent_id: str,
        entries: list[ContextRegistryEntry],
    ) -> ContextRegistry:
        registry = self.load_registry(session_id, tenant_id, group_id, agent_id)
        kept = list(registry.entries)
        kept.extend(entries)
        pruned = self._prune_entries(kept)
        payload = ContextRegistry(
            tenant_id=tenant_id,
            group_id=group_id,
            session_id=session_id,
            entries=tuple(pruned),
        )
        self._registry_path(group_id, agent_id, session_id).write_text(
            json.dumps(payload.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return payload

    def list_recent_entries(
        self,
        session_id: str,
        tenant_id: str,
        group_id: str,
        agent_id: str,
        limit: int = 20,
    ) -> list[ContextRegistryEntry]:
        registry = self.load_registry(session_id, tenant_id, group_id, agent_id)
        return list(registry.entries[-limit:])

    def prune_registry(self, session_id: str, tenant_id: str, group_id: str, agent_id: str) -> ContextRegistry:
        registry = self.load_registry(session_id, tenant_id, group_id, agent_id)
        pruned = ContextRegistry(
            tenant_id=tenant_id,
            group_id=group_id,
            session_id=session_id,
            entries=tuple(self._prune_entries(list(registry.entries))),
        )
        self._registry_path(group_id, agent_id, session_id).write_text(
            json.dumps(pruned.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return pruned

    def _prune_entries(self, entries: list[ContextRegistryEntry]) -> list[ContextRegistryEntry]:
        if not entries:
            return []
        grouped: dict[str, list[ContextRegistryEntry]] = {}
        turn_order: list[str] = []
        for entry in entries:
            grouped.setdefault(entry.source_turn_id, [])
            if entry.source_turn_id not in turn_order:
                turn_order.append(entry.source_turn_id)
            grouped[entry.source_turn_id].append(entry)
        kept_turns = turn_order[-self.max_turns :]
        pruned: list[ContextRegistryEntry] = []
        for turn_id in kept_turns:
            pruned.extend(grouped[turn_id][-self.max_entries_per_turn :])
        return pruned

    def _registry_path(self, group_id: str, agent_id: str, session_id: str) -> Path:
        user_id = self.session_manager._resolve_user_id(group_id, session_id, agent_id)
        if not user_id:
            user_id = self.session_manager.resolve_user_id_any_group(session_id, agent_id)
        if not user_id:
            user_id = "default"
        sessions_dir = self.session_manager._get_user_sessions_path(group_id, user_id)
        return sessions_dir / f"{session_id}.registry.json"
