from __future__ import annotations

from workflow.routes.base import BaseRouteRunner, RouteExecutionRequest
from workflow.types import WorkflowPlan


class RejectRouteRunner(BaseRouteRunner):
    route_name = "reject"

    def run(self, plan: WorkflowPlan, request: RouteExecutionRequest):
        return self._build_payload(
            plan,
            request,
            ("Treat this request as rejected and do not enter the normal execution flow.",),
            status="rejected",
        )
