from __future__ import annotations

from dataclasses import replace
from datetime import datetime

from memory_system.session_working_memory.models import (
    SessionWorkingMemory,
    WorkingMemoryEntry,
    WorkingMemoryHead,
)


class SessionWorkingMemoryRetention:
    def __init__(
        self,
        *,
        active_budget: int = 20,
        max_focus_tasks: int = 2,
        max_resolved_queries: int = 3,
        max_review_outcomes: int = 3,
    ) -> None:
        self.active_budget = active_budget
        self.max_focus_tasks = max_focus_tasks
        self.max_resolved_queries = max_resolved_queries
        self.max_review_outcomes = max_review_outcomes

    def merge(
        self,
        memory: SessionWorkingMemory | None,
        new_entries: list[WorkingMemoryEntry],
    ) -> SessionWorkingMemory:
        current = memory or SessionWorkingMemory()
        existing = [replace(entry) for entry in current.entries]
        if not new_entries:
            return SessionWorkingMemory(entries=existing, head=self._build_head(existing))

        incoming_types = {entry.entry_type for entry in new_entries if entry.entry_type in {"focus_task", "resolved_query", "review_outcome"}}
        updated_entries: list[WorkingMemoryEntry] = []
        for entry in existing:
            if entry.status != "active":
                updated_entries.append(entry)
                continue
            if entry.entry_type in incoming_types:
                updated_entries.append(replace(entry, status="superseded"))
            else:
                updated_entries.append(entry)

        updated_entries.extend(replace(entry) for entry in new_entries)
        updated_entries = self._apply_budget(updated_entries)
        return SessionWorkingMemory(
            entries=updated_entries,
            head=self._build_head(updated_entries),
        )

    def _apply_budget(self, entries: list[WorkingMemoryEntry]) -> list[WorkingMemoryEntry]:
        active_entries = [entry for entry in entries if entry.status == "active"]
        focus_entries = [entry for entry in active_entries if entry.entry_type == "focus_task"]
        resolved_entries = [entry for entry in active_entries if entry.entry_type == "resolved_query"]
        review_entries = [entry for entry in active_entries if entry.entry_type == "review_outcome"]
        preserve_ids = {
            entry.entry_id for entry in focus_entries[-self.max_focus_tasks :]
        } | {
            entry.entry_id for entry in resolved_entries[-self.max_resolved_queries :]
        } | {
            entry.entry_id for entry in review_entries[-self.max_review_outcomes :]
        }

        if len(active_entries) <= self.active_budget:
            return entries

        ranked_active = sorted(active_entries, key=self._entry_sort_key, reverse=True)
        keep_ids = {entry.entry_id for entry in ranked_active[: self.active_budget]} | preserve_ids
        trimmed: list[WorkingMemoryEntry] = []
        for entry in entries:
            if entry.status == "active" and entry.entry_id not in keep_ids:
                trimmed.append(replace(entry, status="stale"))
            else:
                trimmed.append(entry)
        return trimmed

    def _build_head(self, entries: list[WorkingMemoryEntry]) -> WorkingMemoryHead:
        active = [entry for entry in entries if entry.status == "active"]
        ordered_active = sorted(active, key=self._entry_sort_key, reverse=True)
        focus_ids = [entry.entry_id for entry in ordered_active if entry.entry_type == "focus_task"][: self.max_focus_tasks]
        latest_resolved_query_id = next(
            (entry.entry_id for entry in ordered_active if entry.entry_type == "resolved_query"),
            None,
        )
        latest_review_outcome_id = next(
            (entry.entry_id for entry in ordered_active if entry.entry_type == "review_outcome"),
            None,
        )
        return WorkingMemoryHead(
            active_entry_ids=[entry.entry_id for entry in ordered_active],
            current_focus_task_ids=focus_ids,
            latest_resolved_query_id=latest_resolved_query_id,
            latest_review_outcome_id=latest_review_outcome_id,
            updated_at=datetime.now().astimezone().isoformat(timespec="seconds"),
        )

    def _entry_sort_key(self, entry: WorkingMemoryEntry) -> tuple[int, str]:
        type_rank = {
            "focus_task": 5,
            "resolved_query": 4,
            "review_outcome": 4,
            "user_assertion": 3,
            "answer_unit": 2,
        }.get(entry.entry_type, 1)
        return (type_rank, entry.created_at)

