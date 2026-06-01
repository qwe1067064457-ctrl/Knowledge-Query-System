from __future__ import annotations

from typing import Any

from workflow.contracts.graph import ExecutionGraph, GlobalBindingFrame, UnitResult
from workflow.orchestrated.execution_layer.contracts.execution_layer_result import ExecutionRunResult
from workflow.orchestrated.execution_layer.contracts.unit_execution_outcome import (
    UnitExecutionContext,
    UnitExecutionOutcome,
)
from workflow.orchestrated.execution_layer.executors.registry import ExecutorRegistry
from workflow.orchestrated.execution_layer.adapters.context_binding_adapter import build_context_binding_workers
from workflow.orchestrated.execution_layer.adapters.retrieval_adapter import build_retrieval_workers
from workflow.orchestrated.execution_layer.adapters.review_adapter import build_review_workers
from workflow.orchestrated.execution_layer.runtime.langgraph_runtime import LangGraphExecutionRuntime
from workflow.orchestrated.execution_layer.workers.registry import WorkerRegistry


class ExecutionLayer:
    """Execute an `ExecutionGraph` via LangGraph and produce rich intermediate execution results."""

    def __init__(
        self,
        *,
        executor_registry: ExecutorRegistry | None = None,
        runtime: LangGraphExecutionRuntime | None = None,
    ) -> None:
        self.executor_registry = executor_registry or ExecutorRegistry()
        self.runtime = runtime or LangGraphExecutionRuntime()

    def execute(
        self,
        *,
        execution_graph: ExecutionGraph,
        request,
        binding_candidates: list[dict[str, Any]],
        global_binding_frame: GlobalBindingFrame,
        worker_registry: WorkerRegistry | None = None,
        context_binding_power: Any | None = None,
        retrieval_power: Any | None = None,
        review_worker: Any | None = None,
        binding_enable_flag: bool = False,
        allow_retrieval: bool = False,
        llm_factory=None,
        base_dir=None,
        recent_power: str | None = None,
        recent_object_type: str | None = None,
    ) -> ExecutionRunResult:
        worker_registry = worker_registry or self._compat_worker_registry(
            context_binding_power=context_binding_power,
            retrieval_power=retrieval_power,
            review_worker=review_worker,
            request=request,
        )
        unit_map = {unit.unit_id: unit for unit in execution_graph.unit_objs()}

        def build_node(unit_id: str):
            unit = unit_map[unit_id]

            def _node(state):
                state_by_unit = dict(state.get("state_by_unit", {}))
                if not self.runtime.can_execute(unit=unit, state_by_unit=state_by_unit):
                    result = UnitResult(
                        unit_id=unit.unit_id,
                        capability=unit.capability,
                        state="skipped",
                        binding_mode=unit.binding_mode,
                        skipped_reason="dependency_not_completed",
                        output_slot=unit.output_slot,
                    )
                    state_by_unit[unit.unit_id] = "skipped"
                    return {
                        "unit_results": [result],
                        "state_by_unit": state_by_unit,
                        "key_events": [],
                        "evidence_bundles": [],
                        "evidence_candidates": [],
                        "preferred_binding_result": state.get("preferred_binding_result"),
                    }

                executor = self.executor_registry.executor_for(
                    unit=unit,
                    request=request,
                    working_memory=request.context.get("working_memory"),
                )
                unit_context = UnitExecutionContext(
                    unit=unit,
                    request=request,
                    binding_candidates=binding_candidates,
                    global_binding_frame=global_binding_frame,
                    binding_enabled=binding_enable_flag,
                    allow_retrieval=allow_retrieval,
                    base_dir=base_dir,
                    recent_power=recent_power,
                    recent_object_type=recent_object_type,
                )
                outcome = executor.run(
                    unit_context=unit_context,
                    worker_registry=worker_registry,
                    llm_factory=llm_factory,
                    trace_hooks=None,
                )
                result = self._unit_result_from_outcome(unit=unit, outcome=outcome)
                state_by_unit[unit.unit_id] = outcome.unit_state
                preferred_binding_result = state.get("preferred_binding_result")
                if preferred_binding_result is None and outcome.binding_result is not None:
                    preferred_binding_result = outcome.binding_result
                return {
                    "unit_results": [result],
                    "state_by_unit": state_by_unit,
                    "key_events": list(outcome.key_events),
                    "evidence_bundles": [outcome.evidence_bundle] if outcome.evidence_bundle is not None else [],
                    "evidence_candidates": list(outcome.evidence_candidates),
                    "preferred_binding_result": preferred_binding_result,
                }

            return _node

        return self.runtime.run(
            execution_graph=execution_graph,
            build_node=build_node,
        )

    def _compat_worker_registry(
        self,
        *,
        context_binding_power: Any | None,
        retrieval_power: Any | None,
        review_worker: Any | None,
        request,
    ) -> WorkerRegistry:
        registry = WorkerRegistry()
        binding_worker = getattr(context_binding_power, "binding_worker", None) or request.context.get("binding_worker")
        if context_binding_power is not None:
            for worker in build_context_binding_workers(
                context_binding_power=context_binding_power,
                binding_worker=binding_worker,
            ):
                registry.register(worker)
        if retrieval_power is not None and review_worker is not None:
            for worker in build_retrieval_workers(
                retrieval_power=retrieval_power,
                review_worker=review_worker,
            ):
                registry.register(worker)
        if review_worker is not None:
            for worker in build_review_workers(review_worker=review_worker):
                registry.register(worker)
        return registry

    def _unit_result_from_outcome(self, *, unit, outcome: UnitExecutionOutcome) -> UnitResult:
        retrieval_quality_status = "not_applicable"
        if outcome.evidence_bundle is not None:
            retrieval_quality_status = str(outcome.evidence_bundle.quality_summary.get("status", "unknown"))
        used_binding = outcome.binding_result is not None
        return UnitResult(
            unit_id=unit.unit_id,
            capability=unit.capability,
            state=outcome.unit_state,
            binding_mode=unit.binding_mode,
            used_binding=used_binding,
            retrieval_quality_status=retrieval_quality_status,
            output_slot=unit.output_slot,
            skipped_reason=outcome.skipped_reason,
            result_payload=dict(outcome.result_payload),
            notes=tuple(dict.fromkeys([*unit.notes, *outcome.notes])),
        )


ExecutionWorker = ExecutionLayer
