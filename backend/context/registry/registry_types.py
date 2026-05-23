from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal


RegistryObjectType = Literal[
    "claim",
    "evidence_ref",
    "comparison_target",
    "case_or_scenario",
    "question_object",
]


@dataclass(frozen=True)
class ContextRegistryEntry:
    object_id: str
    object_type: RegistryObjectType
    tenant_id: str
    group_id: str
    session_id: str
    source_turn_id: str
    content: str
    refs: tuple[str, ...] = ()
    salience_score: float = 0.0
    source_power: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["refs"] = list(self.refs)
        return payload

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ContextRegistryEntry":
        return cls(
            object_id=str(data["object_id"]),
            object_type=data["object_type"],
            tenant_id=str(data["tenant_id"]),
            group_id=str(data["group_id"]),
            session_id=str(data["session_id"]),
            source_turn_id=str(data["source_turn_id"]),
            content=str(data.get("content", "")),
            refs=tuple(data.get("refs", ())),
            salience_score=float(data.get("salience_score", 0.0) or 0.0),
            source_power=data.get("source_power"),
            metadata=dict(data.get("metadata", {})),
        )


@dataclass(frozen=True)
class ContextRegistry:
    tenant_id: str
    group_id: str
    session_id: str
    entries: tuple[ContextRegistryEntry, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "tenant_id": self.tenant_id,
            "group_id": self.group_id,
            "session_id": self.session_id,
            "entries": [entry.to_dict() for entry in self.entries],
        }
