from __future__ import annotations

from typing import Iterable

from monitoring.core.types import MonitoringEvent


def load_trace_events(events: Iterable[object]) -> list[MonitoringEvent]:
    normalized: list[MonitoringEvent] = []
    for item in events:
        if isinstance(item, MonitoringEvent):
            normalized.append(item)
        elif hasattr(item, "to_dict"):
            normalized.append(MonitoringEvent.from_dict(item.to_dict()))
        elif isinstance(item, dict):
            normalized.append(MonitoringEvent.from_dict(item))
    return sorted(normalized, key=lambda event: (event.started_at, event.event_type))
