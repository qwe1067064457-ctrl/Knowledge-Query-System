from __future__ import annotations

from workflow.runners.base import BaseRouteRunner, RouteExecutionRequest
from workflow.types import WorkflowPlan


class QaRouteRunner(BaseRouteRunner):
    route_name = "qa"

    def run(self, plan: WorkflowPlan, request: RouteExecutionRequest):
        return self._build_payload(
            plan,
            request,
            ("This request should stay within a single-turn answer flow. Keep execution lightweight and avoid unnecessary planning narration.",),
        )
