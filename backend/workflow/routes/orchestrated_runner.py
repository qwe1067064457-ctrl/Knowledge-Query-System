from __future__ import annotations

from dataclasses import replace

from workflow.powers.challenge_power import ChallengePower
from workflow.powers.context_binding_power import ContextBindingPower
from workflow.powers.decomposition_power import DecompositionPower
from workflow.powers.planning_power import PlanningPower
from workflow.powers.retrieval_power import RetrievalPower
from workflow.retrieval_gate import RetrievalGate
from workflow.routes.base import BaseRouteRunner, RouteExecutionRequest
from workflow.types import ContextBindingResult, QueryUnit, WorkflowPlan
from workflow.workers.binding_worker import BindingWorker
from workflow.workers.planner_worker import PlannerWorker
from workflow.workers.review_worker import ReviewWorker


def _merge_key_events(*event_groups: tuple[str, ...] | list[str]) -> tuple[str, ...]:
    merged: list[str] = []
    for group in event_groups:
        for item in group:
            if item and item not in merged:
                merged.append(str(item))
    return tuple(merged)


def _binding_events(binding: ContextBindingResult | None) -> tuple[str, ...]:
    if binding is None:
        return ()
    return ("binding_ambiguous",) if binding.binding_ambiguous else ("binding_applied",)


def _retrieval_events(*, retrieval_quality: dict[str, object], repaired_units: int, missing_evidence: bool) -> tuple[str, ...]:
    events = ["retrieval_performed"]
    if repaired_units > 0:
        events.append("retrieval_repaired")
    if missing_evidence or retrieval_quality.get("status") == "bad":
        events.append("retrieval_quality_weak")
    return tuple(events)


def _challenge_events(challenge) -> tuple[str, ...]:
    events: list[str] = []
    if challenge.follow_up_retrieval_attempted():
        events.append("follow_up_retrieval_attempted")
    if challenge.review_bundle_obj().follow_up_retrieval_improved():
        events.append("follow_up_retrieval_improved")
    if challenge.status == "needs_clarification":
        events.append("clarification_required")
    if challenge.status == "insufficient_evidence":
        events.append("insufficient_evidence")
    return tuple(events)


class OrchestratedRouteRunner(BaseRouteRunner):
    route_name = "orchestrated"

    def __init__(self) -> None:
        self.binding_worker = BindingWorker()
        self.review_worker = ReviewWorker()
        self.planner_worker = PlannerWorker()
        self.context_binding_power = ContextBindingPower(binding_worker=self.binding_worker)
        self.decomposition_power = DecompositionPower()
        self.planning_power = PlanningPower()
        self.retrieval_power = RetrievalPower()
        self.challenge_power = ChallengePower()
        self.retrieval_gate = RetrievalGate()

    def run(self, plan: WorkflowPlan, request: RouteExecutionRequest):
        payload = self._build_payload(
            plan,
            request,
            ("This request requires explicit execution organization. Make the stages or subtask order visible before giving the final answer.",),
        )
        context_bundle = payload.context_bundle_obj()
        answer_constraints = dict(payload.answer_constraints)
        plan_bundle = payload.plan_bundle_obj()
        key_events: tuple[str, ...] = ()

        binding_result: ContextBindingResult | None = None
        binding_candidates = self._registry_binding_candidates(request)
        if "context_binding_power" in plan.enabled_powers:
            candidate_entries = self.context_binding_power.collect_candidates(binding_candidates)
            binding_result = self.context_binding_power.bind(
                request.message,
                candidate_entries,
                recent_messages=request.context.get("recent_messages"),
                llm_call=request.context.get("bound_query_llm_call"),
                base_dir=request.context.get("base_dir"),
                rewrite_query=bool(plan.rewrite_query),
                recent_power=request.context.get("recent_power"),
                recent_object_type=request.context.get("recent_object_type"),
            )
            key_events = _merge_key_events(
                key_events,
                _binding_events(binding_result),
            )
            context_bundle = replace(
                context_bundle,
                binding=binding_result,
                binding_summary=binding_result.binding_summary or "binding_applied",
                candidate_count=len(candidate_entries),
            )
        context_bundle = self._normalize_context_bundle_obj(plan, context_bundle)

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
            plan_bundle = self.planning_power.build_plan_bundle_obj(
                query=request.message,
                task_shape=plan.trace.task_shape,
                task_topology=plan.trace.task_topology,
                query_units=list(query_unit_dicts),
                bound_targets=list(context_bundle.bound_targets()),
                planner_worker=self.planner_worker,
            )
            if query_unit_dicts:
                plan_bundle = replace(plan_bundle, query_units=query_unit_dicts)
            plan_bundle = self._normalize_plan_bundle_obj(plan_bundle)

        evidence_bundle = payload.evidence_bundle
        evidence_candidates = list(self._registry_evidence_candidates(request))
        retrieval_decision = self.retrieval_gate.decide(
            plan=plan,
            request=request,
            binding_result=binding_result,
            query_units=query_units,
        )
        if "retrieval_power" in plan.enabled_powers and retrieval_decision.should_retrieve:
            if query_units:
                units_for_retrieval = query_units
            else:
                target_refs = binding_result.target_refs() if binding_result is not None else ()
                units_for_retrieval = (
                    QueryUnit(
                        unit_id="primary",
                        text=(binding_result.rewritten_query if binding_result is not None and binding_result.rewritten_query else request.message).strip(),
                        origin="primary",
                        target_refs=target_refs,
                    ),
                )
            evidence_bundle = self.retrieval_power.retrieve(units_for_retrieval)
            seen = {candidate.object_id for candidate in evidence_candidates}
            for candidate in evidence_bundle.to_evidence_ref_candidate_objs():
                if candidate.object_id in seen:
                    continue
                seen.add(candidate.object_id)
                evidence_candidates.append(candidate)
            retrieval_quality = self.review_worker.retrieval_quality_check(evidence_bundle=evidence_bundle)
            key_events = _merge_key_events(
                key_events,
                _retrieval_events(
                    retrieval_quality=retrieval_quality,
                    repaired_units=evidence_bundle.repaired_unit_count(),
                    missing_evidence=evidence_bundle.missing_evidence_flag(),
                ),
            )

        review_bundle = payload.review_bundle_obj()
        if "challenge_power" in plan.enabled_powers:
            challenge = self.challenge_power.execute(
                query=request.message,
                rewritten_query=binding_result.rewritten_query if binding_result is not None else None,
                candidate_targets=list(context_bundle.bound_targets()),
                binding_result=binding_result,
                evidence_candidates=evidence_candidates,
                binding_worker=self.binding_worker,
                review_worker=self.review_worker,
                retrieval_power=self.retrieval_power if "retrieval_power" in plan.enabled_powers else None,
            )
            review_bundle = self._normalize_review_bundle_obj(challenge.to_review_bundle())
            answer_constraints.update(challenge.answer_constraints)
            key_events = _merge_key_events(
                key_events,
                _challenge_events(challenge),
            )
            if challenge.status == "needs_clarification" and payload.status == "ready":
                payload = replace(payload, status="needs_clarification")

        return self._finalize_payload(
            payload,
            plan,
            context_bundle=context_bundle,
            plan_bundle=plan_bundle,
            review_bundle=review_bundle,
            answer_constraints=answer_constraints,
            key_events=key_events,
            evidence_bundle=evidence_bundle,
        )
