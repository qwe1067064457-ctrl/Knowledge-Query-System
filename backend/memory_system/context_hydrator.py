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
            limit=None,
        )
        if not entries:
            return []

        if anchor.anchor_spans:
            selected: list[dict[str, Any]] = []
            entry_index = {entry.id: index for index, entry in enumerate(entries)}
            for span in anchor.anchor_spans:
                start_id = str(span.get("start_entry_id") or "").strip()
                end_id = str(span.get("end_entry_id") or "").strip()
                tail_count = int(span.get("tail_count") or 0)
                if start_id and end_id and start_id in entry_index and end_id in entry_index:
                    start = entry_index[start_id]
                    end = entry_index[end_id]
                    if end < start:
                        start, end = end, start
                    left = max(0, start - 1)
                    right = min(len(entries), end + 1)
                    selected.extend(entry.to_dict() for entry in entries[left:right])
                    continue
                if tail_count > 0:
                    selected.extend(entry.to_dict() for entry in entries[-tail_count:])
            if selected:
                deduped: list[dict[str, Any]] = []
                seen_ids: set[str] = set()
                for item in selected:
                    entry_id = str(item.get("id") or "").strip()
                    if entry_id and entry_id in seen_ids:
                        continue
                    if entry_id:
                        seen_ids.add(entry_id)
                    deduped.append(item)
                return deduped[:limit]

        return [entry.to_dict() for entry in entries[-limit:]]
