from __future__ import annotations

from typing import Any

from context.session.session_manager import SessionManager
from memory_system.memory_anchor import MemoryAnchor


class MemoryContextHydrator:
    def hydrate(
        self,
        *,
        anchor: MemoryAnchor,
        session_manager: SessionManager,
        group_id: str,
        agent_id: str,
        limit: int = 12,
    ) -> list[dict[str, Any]]:
        if not anchor.can_hydrate_context or not anchor.source_session_id:
            return []
        entries = session_manager.get_transcript(
            group_id=group_id,
            agent_id=agent_id,
            session_id=anchor.source_session_id,
            limit=limit,
        )
        return [entry.to_dict() for entry in entries]
