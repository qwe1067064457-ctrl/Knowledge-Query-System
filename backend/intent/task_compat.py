from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from intent.types import ResolvedTask, TaskTopology


VALID_TOPOLOGIES: tuple[TaskTopology, ...] = (
    "single",
    "parallel_queries",
    "parallel_subtasks",
    "staged",
)


@dataclass(frozen=True)
class ResolvedTaskCompatibility:
    needs_query_decomposition: bool = False
    needs_agent_planning: bool = False


def build_task_compat(task: ResolvedTask) -> ResolvedTaskCompatibility:
    return ResolvedTaskCompatibility(
        needs_query_decomposition=task.complexity == "compound"
        and task.topology in {"parallel_queries", "parallel_subtasks"},
        needs_agent_planning=task.complexity == "complex",
    )


def infer_topology_from_legacy_task(task_payload: dict[str, Any]) -> TaskTopology:
    topology = task_payload.get("topology")
    if topology in VALID_TOPOLOGIES:
        return topology

    complexity = str(task_payload.get("complexity", "simple"))
    shape = str(task_payload.get("shape", "none"))

    if complexity == "compound" or shape == "multi_question":
        return "parallel_queries"
    return "single"
