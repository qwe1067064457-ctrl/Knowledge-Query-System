from __future__ import annotations

from collections import Counter

from monitoring.core.types import MetricSnapshot, RequestTimeline


def aggregate_metrics(timelines: list[RequestTimeline]) -> MetricSnapshot:
    if not timelines:
        return MetricSnapshot()

    route_distribution: Counter[str] = Counter()
    action_distribution: Counter[str] = Counter()
    answer_latencies: list[int] = []
    answer_successes = 0
    retrieval_requests = 0
    compaction_requests = 0

    for timeline in timelines:
        stage_map = {stage["name"]: stage for stage in timeline.stages}
        workflow_stage = stage_map.get("workflow", {})
        answer_stage = stage_map.get("answer", {})
        route = str(workflow_stage.get("metadata", {}).get("workflow_name", ""))
        action = str(answer_stage.get("output_summary", {}).get("payload_summary", {}).get("action", ""))
        if route:
            route_distribution[route] += 1
        if action:
            action_distribution[action] += 1
        if answer_stage:
            answer_latencies.append(int(answer_stage.get("latency_ms", 0) or 0))
            if answer_stage.get("status") == "success":
                answer_successes += 1
        branch_names = {branch["name"] for branch in timeline.branches}
        context_memory_retrieval = bool(
            stage_map.get("context", {}).get("output_summary", {}).get("memory_retrieval", {}).get("performed", False)
        )
        if "retrieval" in branch_names or context_memory_retrieval:
            retrieval_requests += 1
        if "compaction" in branch_names:
            compaction_requests += 1

    request_count = len(timelines)
    return MetricSnapshot(
        request_count=request_count,
        route_distribution=dict(route_distribution),
        action_distribution=dict(action_distribution),
        answer_success_rate=(answer_successes / request_count) if request_count else 0.0,
        answer_latency_ms={
            "avg": int(sum(answer_latencies) / len(answer_latencies)) if answer_latencies else 0,
            "max": max(answer_latencies) if answer_latencies else 0,
        },
        retrieval_run_rate=(retrieval_requests / request_count) if request_count else 0.0,
        compaction_rate=(compaction_requests / request_count) if request_count else 0.0,
    )
