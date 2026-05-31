from __future__ import annotations

from typing import Any

from workflow.contracts.graph import ExecutionGraph, UnitResult
from workflow.orchestrated.execution_layer.contracts.execution_layer_result import ExecutionLayerResult
from workflow.orchestrated.execution_layer.runtime.conditional_edges import should_execute_unit
from workflow.orchestrated.execution_layer.runtime.graph_builder import LangGraphExecutionGraphBuilder
from workflow.orchestrated.execution_layer.runtime.state import ExecutionRuntimeState
from workflow.types import ContextBindingResult, EvidenceBundle, EvidenceItem, RetrievalUnitResult


class LangGraphExecutionRuntime:
    def __init__(self, *, graph_builder: LangGraphExecutionGraphBuilder | None = None) -> None:
        self.graph_builder = graph_builder or LangGraphExecutionGraphBuilder()

    def run(
        self,
        *,
        execution_graph: ExecutionGraph,
        build_node,
    ) -> ExecutionLayerResult:
        app = self.graph_builder.build(
            execution_graph=execution_graph,
            node_factory=build_node,
        )
        result: ExecutionRuntimeState = app.invoke(
            {
                "execution_graph": execution_graph,
                "unit_results": [],
                "state_by_unit": {},
                "evidence_bundles": [],
                "evidence_candidates": [],
                "key_events": [],
                "preferred_binding_result": None,
            }
        )
        return ExecutionLayerResult(
            execution_graph=execution_graph,
            unit_results=tuple(result["unit_results"]),
            evidence_bundle=self._merge_bundles(result.get("evidence_bundles", [])),
            preferred_binding_result=result.get("preferred_binding_result"),
            evidence_candidates=tuple(result.get("evidence_candidates", [])),
            key_events=tuple(dict.fromkeys(result.get("key_events", []))),
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

