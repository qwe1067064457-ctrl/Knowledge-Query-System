from __future__ import annotations

from typing import Any

from workflow.orchestrated.execution_layer.contracts.execution_layer_result import ExecutionLayerResult, ExecutionRunResult
from workflow.orchestrated.execution_layer.contracts.graph import ExecutionGraph, GlobalBindingFrame
from workflow.orchestrated.execution_layer.engine.state_machine import ExecutionStateMachine
from workflow.orchestrated.execution_layer.executors.registry import CapabilityExecutorRegistry
from workflow.types import ContextBindingResult, EvidenceBundle, EvidenceItem, QueryUnit, RetrievalUnitResult, UnitResult


class ExecutionLayer:
    """Execute an `ExecutionGraph` and produce rich intermediate execution results."""

    def __init__(
        self,
        *,
        executor_registry: CapabilityExecutorRegistry | None = None,
        state_machine: ExecutionStateMachine | None = None,
    ) -> None:
        self.executor_registry = executor_registry or CapabilityExecutorRegistry()
        self.state_machine = state_machine or ExecutionStateMachine()

    def execute(
        self,
        *,
        execution_graph: ExecutionGraph,
        request,
        binding_candidates: list[dict[str, Any]],
        global_binding_frame: GlobalBindingFrame,
        context_binding_power: Any | None = None,
        retrieval_power: Any | None = None,
        review_worker: Any | None = None,
        binding_enable_flag: bool = False,
        allow_retrieval: bool = False,
        llm_call: Any | None = None,
        base_dir=None,
        recent_power: str | None = None,
        recent_object_type: str | None = None,
    ) -> ExecutionRunResult:
        unit_results: list[UnitResult] = []
        key_events: list[str] = []
        evidence_bundles: list[EvidenceBundle] = []
        evidence_candidates: list[dict[str, Any]] = []
        preferred_binding_result: ContextBindingResult | None = None
        state_by_unit: dict[str, str] = {}

        shared_candidate_entries = self._shared_candidate_entries(
            binding_candidates=binding_candidates,
            frame=global_binding_frame,
        )

        for unit_id in execution_graph.topological_unit_ids():
            unit = next((item for item in execution_graph.unit_objs() if item.unit_id == unit_id), None)
            if unit is None:
                continue

            if not self.state_machine.can_proceed(unit=unit, state_by_unit=state_by_unit):
                unit_results.append(
                    UnitResult(
                        unit_id=unit.unit_id,
                        capability=unit.capability,
                        state="skipped",
                        binding_mode=unit.binding_mode,
                        skipped_reason="dependency_not_completed",
                        output_slot=unit.output_slot,
                    )
                )
                state_by_unit[unit.unit_id] = "skipped"
                continue

            binding_result = None
            used_binding = False
            unit_state = "completed"
            skipped_reason: str | None = None
            executor_plan = self.executor_registry.plan_for_unit(
                unit=unit,
                request=request,
                working_memory=request.context.get("working_memory"),
            )
            unit_notes = tuple(dict.fromkeys((*unit.notes, *executor_plan.notes)))
            if executor_plan.terminal_state is not None:
                unit_results.append(
                    UnitResult(
                        unit_id=unit.unit_id,
                        capability=unit.capability,
                        state=executor_plan.terminal_state,
                        binding_mode=unit.binding_mode,
                        used_binding=False,
                        retrieval_quality_status="not_applicable",
                        output_slot=unit.output_slot,
                        skipped_reason=executor_plan.terminal_reason,
                        notes=unit_notes,
                    )
                )
                state_by_unit[unit.unit_id] = executor_plan.terminal_state
                continue
            if binding_enable_flag and context_binding_power is not None and unit.binding_mode != "skip":
                candidate_entries = (
                    shared_candidate_entries
                    if unit.binding_mode == "pre_shared" and shared_candidate_entries
                    else context_binding_power.collect_candidates(binding_candidates)
                )
                binding_result = context_binding_power.bind(
                    executor_plan.effective_goal,
                    candidate_entries,
                    working_memory=request.context.get("working_memory"),
                    recent_messages=request.context.get("recent_messages"),
                    llm_call=llm_call,
                    base_dir=base_dir,
                    rewrite_query=True,
                    recent_power=recent_power,
                    recent_object_type=recent_object_type,
                    memory_anchors=request.context.get("memory_anchors"),
                )
                used_binding = True
                if preferred_binding_result is None and binding_result is not None:
                    preferred_binding_result = binding_result
                if binding_result is not None:
                    key_events.append("binding_applied" if not binding_result.binding_ambiguous else "binding_ambiguous")
                    if binding_result.needs_clarification:
                        key_events.append("binding_needs_clarification")
                        unit_state = "blocked"
                        skipped_reason = "binding_needs_clarification"
                    elif binding_result.fallback_type:
                        key_events.append("binding_fallback")

            retrieval_quality_status = "not_applicable"
            if (
                unit_state != "blocked"
                and allow_retrieval
                and retrieval_power is not None
                and executor_plan.allow_retrieval
                and unit.capability != "synthesis"
            ):
                query_text = (
                    binding_result.rewritten_query
                    if binding_result is not None
                    and binding_result.rewritten_query
                    and str(binding_result.fallback_type or "").strip() != "retrieve_on_raw_query"
                    else executor_plan.effective_goal
                )
                query_unit = QueryUnit(
                    unit_id=unit.unit_id,
                    text=query_text.strip(),
                    origin="primary",
                    target_refs=binding_result.target_refs() if binding_result is not None else (),
                )
                bundle = retrieval_power.retrieve((query_unit,))
                evidence_bundles.append(bundle)
                if review_worker is not None:
                    retrieval_quality = review_worker.retrieval_quality_check(evidence_bundle=bundle)
                    retrieval_quality_status = str(retrieval_quality.get("status", "unknown"))
                    if retrieval_quality_status == "bad":
                        key_events.append("retrieval_quality_weak")
                        unit_state = "degraded"
                        skipped_reason = "retrieval_quality_bad"
                    elif bundle.repaired_unit_count() > 0:
                        key_events.append("retrieval_repaired")
                    else:
                        key_events.append("retrieval_performed")
                for candidate in bundle.to_evidence_ref_candidates():
                    if candidate not in evidence_candidates:
                        evidence_candidates.append(candidate)

            unit_results.append(
                UnitResult(
                    unit_id=unit.unit_id,
                    capability=unit.capability,
                    state=unit_state,
                    binding_mode=unit.binding_mode,
                    used_binding=used_binding,
                    retrieval_quality_status=retrieval_quality_status,
                    output_slot=unit.output_slot,
                    skipped_reason=skipped_reason,
                    notes=unit_notes,
                )
            )
            state_by_unit[unit.unit_id] = unit_state

        merged_bundle = self._merge_bundles(evidence_bundles)
        return ExecutionLayerResult(
            execution_graph=execution_graph,
            unit_results=tuple(unit_results),
            evidence_bundle=merged_bundle,
            preferred_binding_result=preferred_binding_result,
            evidence_candidates=tuple(evidence_candidates),
            key_events=tuple(dict.fromkeys(key_events)),
        )

    def _shared_candidate_entries(
        self,
        *,
        binding_candidates: list[dict[str, Any]],
        frame: GlobalBindingFrame,
    ) -> list[dict[str, Any]]:
        wanted = {item for item in frame.shared_target_candidates if item}
        if not wanted:
            return []
        selected = [
            dict(candidate)
            for candidate in binding_candidates
            if str(candidate.get("object_id") or candidate.get("content") or "").strip() in wanted
        ]
        return selected

    def _merge_bundles(self, bundles: list[EvidenceBundle]) -> EvidenceBundle | None:
        if not bundles:
            return None
        query_unit_results: list[RetrievalUnitResult | dict[str, Any]] = []
        merged_items: dict[tuple[str, str], EvidenceItem] = {}
        source_refs: list[str] = []
        quality_scores: list[float] = []
        repairable_units = 0
        repaired_units = 0
        for bundle in bundles:
            query_unit_results.extend(bundle.query_unit_result_objs())
            for item in bundle.merged_evidence_items:
                key = (item.source_path, item.locator)
                if key not in merged_items:
                    merged_items[key] = item
            for source_ref in bundle.source_ref_list():
                if source_ref not in source_refs:
                    source_refs.append(source_ref)
            quality_scores.append(float(bundle.quality_summary.get("average_weighted_score", 0.0) or 0.0))
            repairable_units += int(bundle.quality_summary.get("repairable_units", 0) or 0)
            repaired_units += int(bundle.quality_summary.get("repaired_units", 0) or 0)
        average_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0.0
        status = "good" if average_quality >= 0.75 else "weak" if average_quality >= 0.45 else "bad"
        return EvidenceBundle(
            query_unit_results=tuple(query_unit_results),
            merged_evidence_items=tuple(merged_items.values()),
            source_refs=tuple(source_refs),
            coverage_summary={"query_units": len(query_unit_results), "sources": len(source_refs)},
            quality_summary={
                "average_weighted_score": round(average_quality, 4),
                "status": status,
                "repairable_units": repairable_units,
                "repaired_units": repaired_units,
            },
            missing_evidence_notes=() if status != "bad" else ("retrieval_quality_weak",),
        )


ExecutionWorker = ExecutionLayer
