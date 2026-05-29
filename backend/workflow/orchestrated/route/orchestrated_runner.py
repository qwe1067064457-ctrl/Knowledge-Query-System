from __future__ import annotations

from dataclasses import replace

from memory_system.session_working_memory import SessionWorkingMemory, SessionWorkingMemoryResolver
from workflow.contracts import ExecutionGraph, ExecutionUnit
from workflow.orchestrated.binding.global_binding_worker import GlobalBindingWorker
from workflow.orchestrated.execution_layer.engine.execution_layer import ExecutionLayer
from workflow.orchestrated.planning.planner_worker import PlannerWorker
from workflow.powers.challenge_power import ChallengePower
from workflow.powers.context_binding_power import ContextBindingPower
from workflow.powers.decomposition_power import DecompositionPower
from workflow.powers.planning_power import PlanningPower
from workflow.powers.retrieval_power import RetrievalPower
from workflow.retrieval_gate import RetrievalGate
from workflow.routes.base import BaseRouteRunner, RouteExecutionRequest
from workflow.types import ContextBindingResult, QueryUnit, UnitResult, WorkflowPlan
from workflow.workers.binding_worker import BindingWorker
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
        self.global_binding_worker = GlobalBindingWorker()
        self.execution_layer = ExecutionLayer()
        self.working_memory_resolver = SessionWorkingMemoryResolver()
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

        binding_candidates = self._registry_binding_candidates(request)
        recent_messages = list(request.context.get("recent_messages") or ())
        working_memory = request.context.get("working_memory")
        memory_anchors = list(request.context.get("memory_anchors") or ())
        global_binding_frame = self.global_binding_worker.build_frame(
            query=request.message,
            candidates=binding_candidates,
            recent_messages=recent_messages,
            working_memory=working_memory,
            memory_anchors=memory_anchors,
            llm_call=request.context.get("global_binding_llm_call") or request.context.get("bound_query_llm_call"),
            base_dir=request.context.get("base_dir"),
        )
        context_bundle = self._normalize_context_bundle_obj(
            plan,
            replace(
                context_bundle,
                global_binding_frame=global_binding_frame,
                candidate_count=len(binding_candidates),
            ),
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
            plan_bundle = self.planning_power.build_plan_bundle_obj(
                query=request.message,
                task_shape=plan.trace.task_shape,
                task_topology=plan.trace.task_topology,
                query_units=list(query_unit_dicts),
                bound_targets=list(context_bundle.bound_targets()),
                global_binding_frame=global_binding_frame,
                binding_enabled=plan.policy_flags.binding_enabled(),
                recent_messages_summary=self._recent_messages_summary(recent_messages),
                working_memory_hints=self._working_memory_hints(request.message, working_memory),
                memory_anchor_hints=self._memory_anchor_hints(memory_anchors),
                llm_call=request.context.get("planning_llm_call") or request.context.get("bound_query_llm_call"),
                base_dir=request.context.get("base_dir"),
                planner_worker=self.planner_worker,
            )
            if query_unit_dicts:
                plan_bundle = replace(plan_bundle, query_units=query_unit_dicts)
            plan_bundle = self._normalize_plan_bundle_obj(plan_bundle)
        elif not plan_bundle.execution_graph_obj().unit_objs():
            fallback_binding_mode = (
                "pre_shared"
                if global_binding_frame.recommended_binding_mode == "global_only" and len(global_binding_frame.shared_target_candidates) == 1
                else "lazy"
                if global_binding_frame.recommended_binding_mode == "selective_per_unit"
                else "lazy"
                if plan.policy_flags.binding_enabled()
                else "skip"
            )
            plan_bundle = replace(
                plan_bundle,
                goal=request.message,
                task_shape=plan.trace.task_shape,
                task_topology=plan.trace.task_topology,
                planning_mode="structured",
                execution_graph=ExecutionGraph(
                    units=(
                        ExecutionUnit(
                            unit_id="unit_primary",
                            goal=request.message,
                            capability="qa_like",
                            output_slot="final_answer",
                            binding_mode=fallback_binding_mode,  # type: ignore[arg-type]
                        ).to_dict(),
                    ),
                    edges=(),
                ),
            )

        retrieval_decision = self.retrieval_gate.decide(
            plan=plan,
            request=request,
            binding_result=None,
            query_units=query_units,
        )
        execution_result = self.execution_layer.execute(
            execution_graph=plan_bundle.execution_graph_obj(),
            request=request,
            binding_candidates=binding_candidates,
            global_binding_frame=global_binding_frame,
            context_binding_power=self.context_binding_power,
            retrieval_power=self.retrieval_power if "retrieval_power" in plan.enabled_powers else None,
            review_worker=self.review_worker,
            binding_enable_flag=plan.policy_flags.binding_enabled(),
            allow_retrieval=retrieval_decision.should_retrieve,
            llm_call=request.context.get("bound_query_llm_call"),
            base_dir=request.context.get("base_dir"),
            recent_power=request.context.get("recent_power"),
            recent_object_type=request.context.get("recent_object_type"),
        )
        binding_result: ContextBindingResult | None = execution_result.preferred_binding_result
        evidence_bundle = execution_result.evidence_bundle
        if binding_result is not None:
            key_events = _merge_key_events(key_events, _binding_events(binding_result))
        key_events = _merge_key_events(key_events, execution_result.key_events)
        if evidence_bundle is not None:
            retrieval_quality = self.review_worker.retrieval_quality_check(evidence_bundle=evidence_bundle)
            key_events = _merge_key_events(
                key_events,
                _retrieval_events(
                    retrieval_quality=retrieval_quality,
                    repaired_units=evidence_bundle.repaired_unit_count(),
                    missing_evidence=evidence_bundle.missing_evidence_flag(),
                ),
            )
        plan_bundle = replace(
            plan_bundle,
            bound_target_refs=(
                binding_result.target_refs()
                if binding_result is not None and binding_result.target_refs()
                else plan_bundle.bound_target_refs
            ),
            unit_results=tuple(item.to_dict() if isinstance(item, UnitResult) else dict(item) for item in execution_result.unit_results),
        )
        context_bundle = self._normalize_context_bundle_obj(
            plan,
            replace(
                context_bundle,
                binding=binding_result,
                binding_summary=(
                    binding_result.binding_summary
                    if binding_result is not None and binding_result.binding_summary
                    else global_binding_frame.recommended_binding_mode
                ),
            ),
        )
        evidence_candidates = list(self._registry_evidence_candidates(request))
        seen_evidence_ids = {candidate.object_id for candidate in evidence_candidates}
        for candidate in execution_result.evidence_candidates:
            object_id = str(candidate.get("object_id") or "").strip()
            if object_id and object_id not in seen_evidence_ids:
                seen_evidence_ids.add(object_id)
                evidence_candidates.append(candidate)

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

    def _recent_messages_summary(self, recent_messages: list[dict[str, str]]) -> list[dict[str, str]]:
        return [
            {
                "role": str(item.get("role") or "").strip(),
                "content": str(item.get("content") or "").strip()[:200],
            }
            for item in recent_messages[-6:]
            if str(item.get("content") or "").strip()
        ]

    def _working_memory_hints(self, query: str, working_memory: SessionWorkingMemory | dict | None) -> list[dict[str, object]]:
        entries = self.working_memory_resolver.build_relevant_entries(
            query=query,
            working_memory=working_memory,
            max_candidates=5,
        )
        return [
            {
                "entry_id": entry.entry_id,
                "entry_type": entry.entry_type,
                "content": entry.content,
                "confidence": entry.confidence,
                "structured_payload": dict(entry.structured_payload),
            }
            for entry in entries
        ]

    def _memory_anchor_hints(self, memory_anchors: list[dict[str, object]]) -> list[dict[str, str]]:
        return [
            {
                "anchor_id": str(item.get("anchor_id") or item.get("source_session_id") or "").strip(),
                "summary": str(item.get("summary") or item.get("content") or "").strip(),
                "confidence": str(item.get("confidence") or "medium").strip(),
            }
            for item in memory_anchors[:5]
            if str(item.get("summary") or item.get("content") or "").strip()
        ]
