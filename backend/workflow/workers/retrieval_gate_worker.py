from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from workflow.runners.base import RouteExecutionRequest
from workflow.types import ContextBindingResult, QueryUnit, WorkflowPlan

RetrievalQueryStrategy = Literal["single", "parallel"]
RetrievalGateReason = Literal[
    "not_needed",
    "knowledge_scope_unclear",
    "scope_info_turn",
    "parallel_queries",
    "challenge_turn",
    "knowledge_query",
    "context_answer_ok",
    "memory_hit_needs_hydrate",
]


@dataclass(frozen=True)
class RetrievalGateDecision:
    should_retrieve: bool
    should_clarify_first: bool = False
    use_memory_first: bool = False
    should_rewrite: bool = False
    query_strategy: RetrievalQueryStrategy = "single"
    reason: RetrievalGateReason = "not_needed"


class RetrievalGateWorker:
    def decide(
        self,
        *,
        plan: WorkflowPlan,
        request: RouteExecutionRequest,
        binding_result: ContextBindingResult | None = None,
        query_units: tuple[QueryUnit, ...] = (),
    ) -> RetrievalGateDecision:
        if plan.knowledge_scope_status == "needs_clarification":
            return RetrievalGateDecision(
                should_retrieve=False,
                should_clarify_first=True,
                reason="knowledge_scope_unclear",
            )
        if plan.handling_mode == "scope_info":
            return RetrievalGateDecision(
                should_retrieve=False,
                reason="scope_info_turn",
            )
        if self._memory_hit_needs_hydrate(
            plan=plan,
            request=request,
            binding_result=binding_result,
        ):
            return RetrievalGateDecision(
                should_retrieve=bool(
                    request.is_knowledge_query
                    or plan.policy_flags.need_retrieval
                    or plan.handling_mode == "challenge"
                ),
                use_memory_first=True,
                should_rewrite=plan.rewrite_query or binding_result is not None,
                query_strategy="single",
                reason="memory_hit_needs_hydrate",
            )
        if plan.trace.task_topology == "parallel_queries" or len(query_units) > 1:
            return RetrievalGateDecision(
                should_retrieve=plan.policy_flags.need_retrieval,
                should_rewrite=plan.rewrite_query,
                query_strategy="parallel",
                reason="parallel_queries",
            )
        if plan.handling_mode == "challenge":
            return RetrievalGateDecision(
                should_retrieve=plan.policy_flags.need_retrieval,
                should_rewrite=plan.rewrite_query or binding_result is not None,
                query_strategy="single",
                reason="challenge_turn",
            )
        if request.is_knowledge_query or plan.policy_flags.need_retrieval:
            return RetrievalGateDecision(
                should_retrieve=True,
                should_rewrite=plan.rewrite_query or binding_result is not None,
                query_strategy="single",
                reason="knowledge_query",
            )
        return RetrievalGateDecision(
            should_retrieve=False,
            should_rewrite=False,
            reason="context_answer_ok",
        )

    def _memory_hit_needs_hydrate(
        self,
        *,
        plan: WorkflowPlan,
        request: RouteExecutionRequest,
        binding_result: ContextBindingResult | None,
    ) -> bool:
        memory_anchors = list(request.context.get("memory_anchors") or ())
        if not memory_anchors:
            return False
        if bool(request.context.get("memory_anchor_summary_sufficient", False)):
            return False
        if bool(request.context.get("hydrated_memory_context")):
            return False
        return bool(
            plan.use_context
            or plan.handling_mode == "challenge"
            or plan.policy_flags.need_context_binding
            or binding_result is not None
        )
