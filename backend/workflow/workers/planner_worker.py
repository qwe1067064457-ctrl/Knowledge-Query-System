from __future__ import annotations

from typing import Any


class PlannerWorker:
    def build_plan(self, *, query: str, task_shape: str, task_topology: str) -> dict[str, Any]:
        return {
            "goal": query,
            "task_shape": task_shape,
            "task_topology": task_topology,
            "ordered_steps": [
                {"step_id": "step_1", "title": "Organize task stages", "status": "planned"},
                {"step_id": "step_2", "title": "Produce route-aware answer", "status": "planned"},
            ],
            "fallback_used": False,
        }
