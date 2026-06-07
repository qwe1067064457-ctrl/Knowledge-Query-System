from __future__ import annotations

from workflow.runners.base import RouteExecutionRequest
from workflow.types import ContextBindingResult, QueryUnit, WorkflowPlan
from workflow.workers.retrieval_gate_worker import RetrievalGateDecision, RetrievalGateWorker


class RetrievalGate:
    def __init__(self, worker: RetrievalGateWorker | None = None) -> None:
        self.worker = worker or RetrievalGateWorker()

    def decide(
        self,
        *,
        plan: WorkflowPlan,
        request: RouteExecutionRequest,
        binding_result: ContextBindingResult | None = None,
        query_units: tuple[QueryUnit, ...] = (),
    ) -> RetrievalGateDecision:
        return self.worker.decide(
            plan=plan,
            request=request,
            binding_result=binding_result,
            query_units=query_units,
        )
