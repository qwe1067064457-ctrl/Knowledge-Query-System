from __future__ import annotations

from workflow.routes.base import BaseRouteRunner
from workflow.routes.chat_runner import ChatRouteRunner
from workflow.routes.orchestrated_runner import OrchestratedRouteRunner
from workflow.routes.qa_runner import QaRouteRunner
from workflow.routes.reject_runner import RejectRouteRunner
from workflow.types import WorkflowPlan


class WorkflowDispatcher:
    def dispatch(self, plan: WorkflowPlan) -> BaseRouteRunner:
        if plan.route == "reject":
            return RejectRouteRunner()
        if plan.route == "chat":
            return ChatRouteRunner()
        if plan.route == "orchestrated":
            return OrchestratedRouteRunner()
        return QaRouteRunner()
