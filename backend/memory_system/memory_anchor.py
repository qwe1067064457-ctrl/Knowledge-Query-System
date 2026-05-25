from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from context.models import MemoryEntry


@dataclass(frozen=True)
class MemoryAnchor:
    memory_type: str
    source: str
    source_session_id: str | None = None
    anchor_key: str | None = None
    can_hydrate_context: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "memory_type": self.memory_type,
            "source": self.source,
            "source_session_id": self.source_session_id,
            "anchor_key": self.anchor_key,
            "can_hydrate_context": self.can_hydrate_context,
        }


class MemoryAnchorBuilder:
    def build(self, entry: MemoryEntry) -> MemoryAnchor:
        anchor_key = None
        if entry.metadata:
            anchor_key = str(entry.metadata.get("id") or entry.metadata.get("anchor_key") or "") or None
        return MemoryAnchor(
            memory_type=entry.memory_type,
            source=entry.source,
            source_session_id=entry.source_session_id,
            anchor_key=anchor_key,
            can_hydrate_context=bool(entry.source_session_id),
        )
