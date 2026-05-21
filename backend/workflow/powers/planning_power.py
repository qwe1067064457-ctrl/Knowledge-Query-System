from __future__ import annotations

from typing import Any


class PlanningPower:
    def build_plan_bundle(
        self,
        *,
        query: str,
        task_shape: str,
        task_topology: str,
        planner_worker: Any | None = None,
    ) -> dict[str, Any]:
        if planner_worker is not None:
            return planner_worker.build_plan(
                query=query,
                task_shape=task_shape,
                task_topology=task_topology,
            )
        return {
            "goal": query,
            "task_shape": task_shape,
            "task_topology": task_topology,
            "ordered_steps": [
                {"step_id": "step_1", "title": "Clarify execution structure", "status": "planned"},
                {"step_id": "step_2", "title": "Produce structured answer", "status": "planned"},
            ],
            "fallback_used": True,
        }
