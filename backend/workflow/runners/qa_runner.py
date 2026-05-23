from __future__ import annotations

from dataclasses import replace

from workflow.powers.challenge_power import ChallengePower
from workflow.powers.context_binding_power import ContextBindingPower
from workflow.powers.retrieval_power import RetrievalPower
from workflow.runners.base import BaseRouteRunner, RouteExecutionRequest
from workflow.types import WorkflowPlan
from workflow.workers.binding_worker import BindingWorker
from workflow.workers.review_worker import ReviewWorker


class QaRouteRunner(BaseRouteRunner):
    route_name = "qa"

    def __init__(self) -> None:
        self.context_binding_power = ContextBindingPower()
        self.challenge_power = ChallengePower()
        self.retrieval_power = RetrievalPower()
        self.binding_worker = BindingWorker()
        self.review_worker = ReviewWorker()

    def run(self, plan: WorkflowPlan, request: RouteExecutionRequest):
        payload = self._build_payload(
            plan,
            request,
            ("This request should stay within a single-turn answer flow. Keep execution lightweight and avoid unnecessary planning narration.",),
        )
        context_bundle = payload.context_bundle_obj()
        answer_constraints = dict(payload.answer_constraints)

        binding_candidates = self._registry_binding_candidates(request)
        if "context_binding_power" in plan.enabled_powers:
            candidate_entries = self.context_binding_power.collect_candidates(binding_candidates)
            binding = self.context_binding_power.bind(
                request.message,
                candidate_entries,
                recent_power=request.context.get("recent_power"),
                recent_object_type=request.context.get("recent_object_type"),
            )
            context_bundle = replace(
                context_bundle,
                binding=binding,
                binding_summary=binding.binding_summary or "binding_applied",
                candidate_count=len(candidate_entries),
            )
        context_bundle = self._normalize_context_bundle_obj(
            plan,
            context_bundle,
        )

        review_bundle = payload.review_bundle_obj()
        if "challenge_power" in plan.enabled_powers:
            evidence_candidates = self._registry_evidence_candidates(request)
            challenge = self.challenge_power.execute(
                query=request.message,
                candidate_targets=list(context_bundle.bound_targets()),
                evidence_candidates=evidence_candidates,
                binding_worker=self.binding_worker,
                review_worker=self.review_worker,
                retrieval_power=self.retrieval_power if "retrieval_power" in plan.enabled_powers else None,
            )
            review_bundle = self._normalize_review_bundle_obj(challenge.to_review_bundle())
            answer_constraints.update(challenge.answer_constraints)
            if challenge.status == "needs_clarification" and payload.status == "ready":
                payload = replace(payload, status="needs_clarification")

        review_bundle = self._normalize_review_bundle_obj(review_bundle)

        return self._finalize_payload(
            payload,
            plan,
            context_bundle=context_bundle,
            plan_bundle=payload.plan_bundle,
            review_bundle=review_bundle,
            answer_constraints=answer_constraints,
        )
