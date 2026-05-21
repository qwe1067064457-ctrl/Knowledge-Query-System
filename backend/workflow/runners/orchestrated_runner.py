from __future__ import annotations

from workflow.runners.base import BaseRouteRunner, RouteExecutionRequest
from workflow.types import WorkflowPlan


class OrchestratedRouteRunner(BaseRouteRunner):
    route_name = "orchestrated"

    def run(self, plan: WorkflowPlan, request: RouteExecutionRequest):
        return self._build_payload(
            plan,
            request,
            ("This request requires explicit execution organization. Make the stages or subtask order visible before giving the final answer.",),
        )
