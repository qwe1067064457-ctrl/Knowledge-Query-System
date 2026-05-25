from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class SessionWorkingMemory:
    current_goal: str | None = None
    rewritten_query: str | None = None
    unresolved_questions: list[str] = field(default_factory=list)
    key_intermediate_conclusions: list[str] = field(default_factory=list)
    supporting_evidence_refs: list[str] = field(default_factory=list)
    next_step_hint: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "current_goal": self.current_goal,
            "rewritten_query": self.rewritten_query,
            "unresolved_questions": [str(item) for item in self.unresolved_questions if str(item).strip()],
            "key_intermediate_conclusions": [
                str(item) for item in self.key_intermediate_conclusions if str(item).strip()
            ],
            "supporting_evidence_refs": [str(item) for item in self.supporting_evidence_refs if str(item).strip()],
            "next_step_hint": self.next_step_hint,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "SessionWorkingMemory":
        payload = dict(data or {})
        return cls(
            current_goal=str(payload["current_goal"]) if payload.get("current_goal") else None,
            rewritten_query=str(payload["rewritten_query"]) if payload.get("rewritten_query") else None,
            unresolved_questions=[str(item) for item in payload.get("unresolved_questions", ()) if str(item).strip()],
            key_intermediate_conclusions=[
                str(item)
                for item in payload.get("key_intermediate_conclusions", ())
                if str(item).strip()
            ],
            supporting_evidence_refs=[
                str(item) for item in payload.get("supporting_evidence_refs", ()) if str(item).strip()
            ],
            next_step_hint=str(payload["next_step_hint"]) if payload.get("next_step_hint") else None,
            metadata=dict(payload.get("metadata", {})),
        )
