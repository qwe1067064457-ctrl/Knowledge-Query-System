from __future__ import annotations

from typing import Any

from workflow.contracts.graph import ExecutionGraph, UnitResult
from workflow.orchestrated.execution_layer.contracts.execution_layer_result import ExecutionLayerResult
from workflow.orchestrated.execution_layer.scheduler.group_planner import ExecutionGroupPlanner
from workflow.orchestrated.execution_layer.scheduler.retry_policy import GroupRetryPolicy
from workflow.orchestrated.execution_layer.runtime.conditional_edges import should_execute_unit
from workflow.orchestrated.execution_layer.runtime.graph_builder import LangGraphExecutionGraphBuilder
from workflow.orchestrated.execution_layer.runtime.state import ExecutionRuntimeState
from workflow.types import ContextBindingResult, EvidenceBundle, EvidenceItem, RetrievalUnitResult


class LangGraphExecutionRuntime:
    def __init__(
        self,
        *,
        graph_builder: LangGraphExecutionGraphBuilder | None = None,
        group_planner: ExecutionGroupPlanner | None = None,
        retry_policy: GroupRetryPolicy | None = None,
    ) -> None:
        self.graph_builder = graph_builder or LangGraphExecutionGraphBuilder()
        self.group_planner = group_planner or ExecutionGroupPlanner()
        self.retry_policy = retry_policy or GroupRetryPolicy()

    def run(
        self,
        *,
        execution_graph: ExecutionGraph,
        build_node,
    ) -> ExecutionLayerResult:
        state: ExecutionRuntimeState = {
            "execution_graph": execution_graph,
            "unit_results": [],
            "state_by_unit": {},
            "evidence_bundles": [],
            "evidence_candidates": [],
            "key_events": [],
            "preferred_binding_result": None,
        }
        all_degraded_units: list[str] = []
        clarification_required = False
        for group_unit_ids in self.group_planner.groups_for(execution_graph):
            retry_count = 0
            state_before_group = self._copy_state(state)
            while True:
                group_graph = self._group_graph(execution_graph=execution_graph, unit_ids=group_unit_ids)
                app = self.graph_builder.build(
                    execution_graph=group_graph,
                    node_factory=build_node,
                )
                result: ExecutionRuntimeState = app.invoke(state_before_group)
                group_results = [
                    item
                    for item in result.get("unit_results", [])[len(state_before_group.get("unit_results", [])) :]
                    if getattr(item, "unit_id", None) in set(group_unit_ids)
                ]
                group_states = tuple(str(getattr(item, "state", "")) for item in group_results)
                if any(
                    str(getattr(item, "state", "")) == "blocked"
                    and str(getattr(item, "skipped_reason", "")) == "binding_needs_clarification"
                    for item in group_results
                ):
                    result["key_events"] = [*result.get("key_events", []), "clarification_required"]
                    state = result
                    clarification_required = True
                    break
                if self.retry_policy.should_retry(states=group_states, retry_count=retry_count):
                    retry_count += 1
                    continue
                all_degraded_units.extend(self.retry_policy.degraded_unit_ids(unit_results=group_results))
                state = result
                break
            if clarification_required:
                break
        return ExecutionLayerResult(
            execution_graph=execution_graph,
            unit_results=tuple(state["unit_results"]),
            evidence_bundle=self._merge_bundles(state.get("evidence_bundles", [])),
            preferred_binding_result=state.get("preferred_binding_result"),
            evidence_candidates=tuple(state.get("evidence_candidates", [])),
            key_events=tuple(dict.fromkeys(state.get("key_events", []))),
            degraded_units=tuple(dict.fromkeys(all_degraded_units)),
            clarification_required=clarification_required,
        )

    def can_execute(self, *, unit, state_by_unit: dict[str, str]) -> bool:
        return should_execute_unit(unit=unit, state_by_unit=state_by_unit)

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

    def _copy_state(self, state: ExecutionRuntimeState) -> ExecutionRuntimeState:
        return {
            "execution_graph": state["execution_graph"],
            "unit_results": list(state.get("unit_results", [])),
            "state_by_unit": dict(state.get("state_by_unit", {})),
            "evidence_bundles": list(state.get("evidence_bundles", [])),
            "evidence_candidates": list(state.get("evidence_candidates", [])),
            "key_events": list(state.get("key_events", [])),
            "preferred_binding_result": state.get("preferred_binding_result"),
        }

    def _group_graph(self, *, execution_graph: ExecutionGraph, unit_ids: tuple[str, ...]) -> ExecutionGraph:
        wanted = set(unit_ids)
        units = tuple(unit.to_dict() for unit in execution_graph.unit_objs() if unit.unit_id in wanted)
        return ExecutionGraph(units=units, edges=(), graph_notes=("execution_group",))

