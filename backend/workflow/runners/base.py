from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any

from workflow.adapters.workflow_registry_consumer import (
    binding_candidates,
    evidence_candidates,
    normalize_registry_entries,
)
from workflow.types import ContextBundle, EvidenceRefCandidate, ExecutionPayload, PlanBundle, ReviewBundle, WorkflowPlan


@dataclass
class RouteExecutionRequest:
    message: str
    messages: list[dict[str, str]]
    is_knowledge_query: bool = False
    context: dict[str, Any] = field(default_factory=dict)


class BaseRouteRunner:
    route_name = "base"

    def run(self, plan: WorkflowPlan, request: RouteExecutionRequest) -> ExecutionPayload:
        return self._build_payload(plan, request, ())

    def _build_payload(
        self,
        plan: WorkflowPlan,
        request: RouteExecutionRequest,
        extra_instructions: tuple[str, ...],
        *,
        status: str = "ready",
    ) -> ExecutionPayload:
        instructions = list(extra_instructions)
        if plan.policy_flags.ask_clarification_first:
            instructions.append(
                "The current request is not ready for full execution yet. Ask a concise clarification question first and do not continue into a substantive answer."
            )
            if plan.trace.missing_context_types:
                missing = ", ".join(plan.trace.missing_context_types)
                instructions.append(f"Focus the clarification on these missing context types: {missing}.")
        if plan.handling_mode == "challenge":
            instructions.append(
                "Treat this as a challenge/correction turn. Re-evaluate the disputed point carefully, explain the basis, and avoid defending the previous answer blindly."
            )
        elif plan.handling_mode == "scope_info":
            instructions.append(
                "Treat this as a scope/capability question. Answer about what the system can or cannot do instead of executing the underlying task."
            )
        elif plan.handling_mode == "unsupported":
            instructions.append(
                "Treat this as an unsupported request. Refuse the operation briefly and, when possible, suggest a safer alternative."
            )

        if plan.use_planner:
            instructions.append("Use an internal lightweight plan before answering so the reasoning order is stable.")
        if plan.decompose_query:
            instructions.append("Cover each sub-question explicitly so no requested branch is skipped.")
        if plan.cite_sources:
            instructions.append("Provide supporting basis or citations when available, and make the grounding visible.")
        if plan.use_context:
            instructions.append("Use the current conversation context and do not treat this as a standalone fresh request.")
        if plan.knowledge_scope_status == "needs_clarification":
            instructions.append("The request implies switching knowledge scope, but the target group is unclear. Ask which knowledge group to search before retrieval.")
            status = "needs_clarification"

        return ExecutionPayload(
            route=plan.route,
            handling_mode=plan.handling_mode,
            action=plan.action,
            status=status,
            enabled_powers=plan.enabled_powers,
            instructions=tuple(instructions),
            knowledge_scope_status=plan.knowledge_scope_status,
            context_bundle=self._default_context_bundle(plan),
            plan_bundle=self._default_plan_bundle(),
            review_bundle=self._default_review_bundle(),
            answer_constraints={
                "cite_sources": plan.cite_sources,
                "use_context": plan.use_context,
            },
            notes=plan.notes,
        )

    def _default_context_bundle(self, plan: WorkflowPlan) -> dict[str, Any]:
        return self._default_context_bundle_obj(plan).to_dict()

    def _default_context_bundle_obj(self, plan: WorkflowPlan) -> ContextBundle:
        return ContextBundle(
            trace=plan.trace.to_dict(),
            binding=None,
            binding_summary="not_applicable",
            candidate_count=0,
            query_units=(),
        )

    def _default_plan_bundle(self) -> dict[str, Any]:
        return self._default_plan_bundle_obj().to_dict()

    def _default_plan_bundle_obj(self) -> PlanBundle:
        return PlanBundle()

    def _default_review_bundle(self) -> dict[str, Any]:
        return self._default_review_bundle_obj().to_dict()

    def _default_review_bundle_obj(self) -> ReviewBundle:
        return ReviewBundle()

    def _normalize_context_bundle(self, plan: WorkflowPlan, context_bundle: dict[str, Any] | None) -> dict[str, Any]:
        return self._normalize_context_bundle_obj(plan, context_bundle).to_dict()

    def _normalize_context_bundle_obj(
        self,
        plan: WorkflowPlan,
        context_bundle: ContextBundle | dict[str, Any] | None,
    ) -> ContextBundle:
        if isinstance(context_bundle, ContextBundle):
            return context_bundle
        return ContextBundle.from_dict(context_bundle, default_trace=plan.trace.to_dict())

    def _normalize_plan_bundle(self, plan_bundle: dict[str, Any] | None) -> dict[str, Any]:
        return self._normalize_plan_bundle_obj(plan_bundle).to_dict()

    def _normalize_plan_bundle_obj(self, plan_bundle: PlanBundle | dict[str, Any] | None) -> PlanBundle:
        if isinstance(plan_bundle, PlanBundle):
            return plan_bundle
        return PlanBundle.from_dict(plan_bundle)

    def _normalize_review_bundle(self, review_bundle: dict[str, Any] | None) -> dict[str, Any]:
        return self._normalize_review_bundle_obj(review_bundle).to_dict()

    def _normalize_review_bundle_obj(self, review_bundle: ReviewBundle | dict[str, Any] | None) -> ReviewBundle:
        if isinstance(review_bundle, ReviewBundle):
            return review_bundle
        return ReviewBundle.from_dict(review_bundle)

    def _finalize_payload(
        self,
        payload: ExecutionPayload,
        plan: WorkflowPlan,
        *,
        context_bundle: ContextBundle | dict[str, Any] | None = None,
        plan_bundle: PlanBundle | dict[str, Any] | None = None,
        review_bundle: ReviewBundle | dict[str, Any] | None = None,
        answer_constraints: dict[str, Any] | None = None,
        status: str | None = None,
    ) -> ExecutionPayload:
        normalized_context = self._normalize_context_bundle_obj(
            plan,
            payload.context_bundle if context_bundle is None else context_bundle,
        )
        normalized_plan = self._normalize_plan_bundle_obj(
            payload.plan_bundle if plan_bundle is None else plan_bundle,
        )
        normalized_review = self._normalize_review_bundle_obj(
            payload.review_bundle if review_bundle is None else review_bundle,
        )
        return replace(
            payload,
            status=payload.status if status is None else status,
            context_bundle=normalized_context.to_dict(),
            plan_bundle=normalized_plan.to_dict(),
            review_bundle=normalized_review.to_dict(),
            answer_constraints=dict(payload.answer_constraints if answer_constraints is None else answer_constraints),
        )

    def _registry_candidates(self, request: RouteExecutionRequest) -> list[dict[str, Any]]:
        return normalize_registry_entries(request.context.get("registry_entries", ()))

    def _registry_binding_candidates(self, request: RouteExecutionRequest) -> list[dict[str, Any]]:
        return binding_candidates(request.context.get("registry_entries", ()))

    def _registry_evidence_candidates(self, request: RouteExecutionRequest) -> list[EvidenceRefCandidate]:
        return evidence_candidates(request.context.get("registry_entries", ()))
