from __future__ import annotations

from dataclasses import replace

from workflow.powers.challenge_power import ChallengePower
from workflow.powers.context_binding_power import ContextBindingPower
from workflow.powers.decomposition_power import DecompositionPower
from workflow.powers.planning_power import PlanningPower
from workflow.powers.retrieval_power import RetrievalPower
from workflow.runners.base import BaseRouteRunner, RouteExecutionRequest
from workflow.types import WorkflowPlan
from workflow.workers.binding_worker import BindingWorker
from workflow.workers.planner_worker import PlannerWorker
from workflow.workers.review_worker import ReviewWorker


class OrchestratedRouteRunner(BaseRouteRunner):
    route_name = "orchestrated"

    def __init__(self) -> None:
        self.context_binding_power = ContextBindingPower()
        self.decomposition_power = DecompositionPower()
        self.planning_power = PlanningPower()
        self.challenge_power = ChallengePower()
        self.retrieval_power = RetrievalPower()
        self.binding_worker = BindingWorker()
        self.planner_worker = PlannerWorker()
        self.review_worker = ReviewWorker()

    def run(self, plan: WorkflowPlan, request: RouteExecutionRequest):
        payload = self._build_payload(
            plan,
            request,
            ("This request requires explicit execution organization. Make the stages or subtask order visible before giving the final answer.",),
        )
        context_bundle = payload.context_bundle_obj()
        answer_constraints = dict(payload.answer_constraints)
        plan_bundle = payload.plan_bundle_obj()
        review_bundle = payload.review_bundle_obj()

        candidates = self._registry_candidates(request)
        candidate_entries = candidates
        if "context_binding_power" in plan.enabled_powers:
            candidate_entries = self.context_binding_power.collect_candidates(candidates)
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

        query_units = ()
        query_unit_dicts: tuple[dict[str, object], ...] = ()
        if "decomposition_power" in plan.enabled_powers:
            query_units = self.decomposition_power.split_parallel_queries(request.message)
            query_unit_dicts = tuple(unit.to_dict() for unit in query_units)
            context_bundle = self._normalize_context_bundle_obj(
                plan,
                replace(context_bundle, query_units=query_unit_dicts),
            )

        if "planning_power" in plan.enabled_powers:
            bound_targets = list(context_bundle.bound_targets())
            plan_bundle = self.planning_power.build_plan_bundle_obj(
                query=request.message,
                task_shape=plan.trace.task_shape,
                task_topology=plan.trace.task_topology,
                query_units=list(query_unit_dicts),
                bound_targets=bound_targets,
                planner_worker=self.planner_worker,
            )
            if query_unit_dicts:
                plan_bundle = replace(plan_bundle, query_units=query_unit_dicts)
            plan_bundle = self._normalize_plan_bundle_obj(plan_bundle)

        if "challenge_power" in plan.enabled_powers:
            evidence_candidates = self._registry_evidence_candidates(request)
            challenge = self.challenge_power.execute(
                query=request.message,
                candidate_targets=list(context_bundle.bound_targets()) or candidate_entries,
                evidence_candidates=evidence_candidates,
                binding_worker=self.binding_worker,
                review_worker=self.review_worker,
                retrieval_power=self.retrieval_power if "retrieval_power" in plan.enabled_powers else None,
            )
            review_bundle = self._normalize_review_bundle_obj(challenge.to_review_bundle())
            answer_constraints.update(challenge.answer_constraints)
            if challenge.status == "needs_clarification" and payload.status == "ready":
                payload = replace(payload, status="needs_clarification")

        plan_bundle = self._normalize_plan_bundle_obj(plan_bundle)
        review_bundle = self._normalize_review_bundle_obj(review_bundle)

        return self._finalize_payload(
            payload,
            plan,
            context_bundle=context_bundle,
            plan_bundle=plan_bundle,
            review_bundle=review_bundle,
            answer_constraints=answer_constraints,
        )
