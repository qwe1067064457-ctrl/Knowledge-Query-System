from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _normalize_confidence(value: Any) -> str:
    text = str(value or "medium").strip().lower()
    if text not in {"high", "medium", "low"}:
        return "medium"
    return text


def _normalize_status(value: Any) -> str:
    text = str(value or "active").strip().lower()
    if text not in {"active", "superseded", "stale"}:
        return "active"
    return text


@dataclass
class WorkingMemoryEntry:
    entry_id: str
    entry_type: str
    turn_id: str
    source_kind: str
    source_ref: str
    content: str
    structured_payload: dict[str, Any] = field(default_factory=dict)
    confidence: str = "medium"
    status: str = "active"
    created_at: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "entry_id": str(self.entry_id),
            "entry_type": str(self.entry_type),
            "turn_id": str(self.turn_id),
            "source_kind": str(self.source_kind),
            "source_ref": str(self.source_ref),
            "content": str(self.content).strip(),
            "structured_payload": dict(self.structured_payload),
            "confidence": _normalize_confidence(self.confidence),
            "status": _normalize_status(self.status),
            "created_at": str(self.created_at or _now_iso()),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any] | None) -> "WorkingMemoryEntry":
        data = dict(payload or {})
        return cls(
            entry_id=str(data.get("entry_id") or "").strip(),
            entry_type=str(data.get("entry_type") or "").strip(),
            turn_id=str(data.get("turn_id") or "").strip(),
            source_kind=str(data.get("source_kind") or "").strip(),
            source_ref=str(data.get("source_ref") or "").strip(),
            content=str(data.get("content") or "").strip(),
            structured_payload=dict(data.get("structured_payload", {}) or {}),
            confidence=_normalize_confidence(data.get("confidence")),
            status=_normalize_status(data.get("status")),
            created_at=str(data.get("created_at") or _now_iso()),
        )


@dataclass
class WorkingMemoryHead:
    active_entry_ids: list[str] = field(default_factory=list)
    current_focus_task_ids: list[str] = field(default_factory=list)
    latest_resolved_query_id: str | None = None
    latest_review_outcome_id: str | None = None
    updated_at: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "active_entry_ids": [str(item) for item in self.active_entry_ids if str(item).strip()],
            "current_focus_task_ids": [str(item) for item in self.current_focus_task_ids if str(item).strip()],
            "latest_resolved_query_id": str(self.latest_resolved_query_id) if self.latest_resolved_query_id else None,
            "latest_review_outcome_id": (
                str(self.latest_review_outcome_id) if self.latest_review_outcome_id else None
            ),
            "updated_at": str(self.updated_at or _now_iso()),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any] | None) -> "WorkingMemoryHead":
        data = dict(payload or {})
        return cls(
            active_entry_ids=[str(item) for item in data.get("active_entry_ids", ()) if str(item).strip()],
            current_focus_task_ids=[str(item) for item in data.get("current_focus_task_ids", ()) if str(item).strip()],
            latest_resolved_query_id=(
                str(data["latest_resolved_query_id"]) if data.get("latest_resolved_query_id") else None
            ),
            latest_review_outcome_id=(
                str(data["latest_review_outcome_id"]) if data.get("latest_review_outcome_id") else None
            ),
            updated_at=str(data.get("updated_at") or _now_iso()),
        )


@dataclass
class SessionWorkingMemory:
    entries: list[WorkingMemoryEntry] = field(default_factory=list)
    head: WorkingMemoryHead = field(default_factory=WorkingMemoryHead)

    def to_dict(self) -> dict[str, Any]:
        return {
            "entries": [entry.to_dict() for entry in self.entries],
            "head": self.head.to_dict(),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any] | None) -> "SessionWorkingMemory":
        data = dict(payload or {})
        if "entries" in data or "head" in data:
            return cls(
                entries=[WorkingMemoryEntry.from_dict(item) for item in data.get("entries", ()) or ()],
                head=WorkingMemoryHead.from_dict(data.get("head")),
            )
        legacy_entries: list[WorkingMemoryEntry] = []
        if data.get("current_goal"):
            legacy_entries.append(
                WorkingMemoryEntry(
                    entry_id="legacy_focus_task",
                    entry_type="focus_task",
                    turn_id="legacy",
                    source_kind="legacy_metadata",
                    source_ref="legacy:current_goal",
                    content=str(data.get("current_goal") or "").strip(),
                    confidence="high",
                )
            )
        if data.get("rewritten_query"):
            legacy_entries.append(
                WorkingMemoryEntry(
                    entry_id="legacy_resolved_query",
                    entry_type="resolved_query",
                    turn_id="legacy",
                    source_kind="legacy_metadata",
                    source_ref="legacy:rewritten_query",
                    content=str(data.get("rewritten_query") or "").strip(),
                    confidence="medium",
                )
            )
        for index, item in enumerate(data.get("key_intermediate_conclusions", ()) or (), start=1):
            text = str(item).strip()
            if text:
                legacy_entries.append(
                    WorkingMemoryEntry(
                        entry_id=f"legacy_review_outcome_{index}",
                        entry_type="review_outcome",
                        turn_id="legacy",
                        source_kind="legacy_metadata",
                        source_ref=f"legacy:key_intermediate_conclusions:{index}",
                        content=text,
                        confidence="medium",
                    )
                )
        head = WorkingMemoryHead(
            active_entry_ids=[entry.entry_id for entry in legacy_entries],
            current_focus_task_ids=[
                entry.entry_id for entry in legacy_entries if entry.entry_type == "focus_task"
            ],
            latest_resolved_query_id=next(
                (entry.entry_id for entry in reversed(legacy_entries) if entry.entry_type == "resolved_query"),
                None,
            ),
            latest_review_outcome_id=next(
                (entry.entry_id for entry in reversed(legacy_entries) if entry.entry_type == "review_outcome"),
                None,
            ),
        )
        return cls(entries=legacy_entries, head=head)

    def active_entries(self) -> list[WorkingMemoryEntry]:
        active_ids = set(self.head.active_entry_ids)
        return [entry for entry in self.entries if entry.entry_id in active_ids and entry.status == "active"]

