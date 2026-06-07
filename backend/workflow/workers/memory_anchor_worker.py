from __future__ import annotations

from typing import Any

from context.models import MemoryEntry
from context.session.session_manager import SessionManager
from memory_system.context_hydrator import MemoryContextHydrator
from memory_system.memory_anchor import MemoryAnchor, MemoryAnchorBuilder


class MemoryAnchorWorker:
    def __init__(
        self,
        builder: MemoryAnchorBuilder | None = None,
        hydrator: MemoryContextHydrator | None = None,
    ) -> None:
        self.builder = builder or MemoryAnchorBuilder()
        self.hydrator = hydrator or MemoryContextHydrator()

    def build_anchor(self, entry: MemoryEntry) -> MemoryAnchor:
        return self.builder.build(entry)

    def hydrate_context(
        self,
        *,
        anchor: MemoryAnchor,
        session_manager: SessionManager,
        group_id: str,
        agent_id: str,
        limit: int = 12,
    ) -> list[dict[str, Any]]:
        return self.hydrator.hydrate(
            anchor=anchor,
            session_manager=session_manager,
            group_id=group_id,
            agent_id=agent_id,
            limit=limit,
        )
