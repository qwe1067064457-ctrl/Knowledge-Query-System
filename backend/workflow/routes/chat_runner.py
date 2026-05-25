from __future__ import annotations

from workflow.routes.base import BaseRouteRunner, RouteExecutionRequest
from workflow.types import WorkflowPlan


class ChatRouteRunner(BaseRouteRunner):
    route_name = "chat"

    def run(self, plan: WorkflowPlan, request: RouteExecutionRequest):
        return self._build_payload(
            plan,
            request,
            ("This is a chat turn. Respond naturally and do not over-structure the answer.",),
        )
