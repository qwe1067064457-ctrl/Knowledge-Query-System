from __future__ import annotations

from collections import Counter

from monitoring.core.types import RequestTimeline


def classify_failures(timelines: list[RequestTimeline]) -> dict[str, int]:
    failures: Counter[str] = Counter()
    for timeline in timelines:
        for stage in timeline.stages:
            if stage.get("status") != "success":
                failures[f"{stage['name']}_failed"] += 1
        for branch in timeline.branches:
            if branch.get("status") == "failed":
                failures[f"{branch['name']}_failed"] += 1
    return dict(failures)
