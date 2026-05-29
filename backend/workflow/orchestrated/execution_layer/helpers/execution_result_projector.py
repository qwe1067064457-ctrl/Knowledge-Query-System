from __future__ import annotations

from workflow.orchestrated.execution_layer.contracts.execution_layer_result import ExecutionLayerResult


def summarize_execution_layer_result(result: ExecutionLayerResult) -> dict[str, object]:
    states = {"completed": [], "degraded": [], "blocked": [], "skipped": []}
    for item in result.unit_results:
        bucket = states.get(item.state)
        if bucket is not None:
            bucket.append(item.unit_id)
    return {
        "topology": result.execution_graph.summary_dict(),
        "completed_units": tuple(states["completed"]),
        "degraded_units": tuple(states["degraded"]),
        "blocked_units": tuple(states["blocked"]),
        "skipped_units": tuple(states["skipped"]),
    }
