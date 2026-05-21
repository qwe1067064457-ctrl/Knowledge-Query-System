from __future__ import annotations

from workflow.runners.base import BaseRouteRunner
from workflow.runners.chat_runner import ChatRouteRunner
from workflow.runners.orchestrated_runner import OrchestratedRouteRunner
from workflow.runners.qa_runner import QaRouteRunner
from workflow.runners.reject_runner import RejectRouteRunner
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
