from __future__ import annotations

from workflow.contracts import ExecutionEdge, ExecutionGraph, ExecutionUnit, GlobalBindingFrame
from workflow.orchestrated.planning.grouped_unit_contracts import GroupedUnitPlan, grouped_plan_from_payload


class GroupedUnitPlanner:
    """Validate grouped planner JSON and project it into the execution graph contract."""

    def parse(self, payload: dict, *, require_synthesis_for_complex: bool = True) -> GroupedUnitPlan:
        return grouped_plan_from_payload(payload, require_synthesis_for_complex=require_synthesis_for_complex)

    def to_execution_graph(
        self,
        plan: GroupedUnitPlan,
        *,
        global_binding_frame: GlobalBindingFrame | None = None,
        binding_enabled: bool = False,
    ) -> ExecutionGraph:
        frame = global_binding_frame or GlobalBindingFrame()
        units: list[ExecutionUnit] = []
        edges: list[ExecutionEdge] = []
        previous_group_ids: tuple[str, ...] = ()
        for group in plan.unit_groups:
            current_group_ids = tuple(unit.unit_id for unit in group)
            for unit in group:
                depends_on = previous_group_ids
                units.append(
                    ExecutionUnit(
                        unit_id=unit.unit_id,
                        goal=unit.query,
                        capability=unit.capability,
                        depends_on=depends_on,
                        proceed_if="all_dependencies_completed" if depends_on else None,
                        output_slot="final_answer" if unit.capability == "synthesis" else unit.unit_id,
                        binding_mode=self._binding_mode(frame=frame, binding_enabled=binding_enabled, capability=unit.capability),
                        retrieval_mode="skip" if unit.capability in {"compare", "synthesis"} else "auto",
                    )
                )
                for dependency_id in depends_on:
                    edges.append(ExecutionEdge(from_unit_id=dependency_id, to_unit_id=unit.unit_id))
            previous_group_ids = current_group_ids
        return ExecutionGraph(
            units=tuple(unit.to_dict() for unit in units),
            edges=tuple(edge.to_dict() for edge in edges),
            graph_notes=("grouped_unit_plan",),
        )

    def _binding_mode(self, *, frame: GlobalBindingFrame, binding_enabled: bool, capability: str) -> str:
        if capability == "synthesis":
            return "skip"
        if frame.recommended_binding_mode == "global_only" and len(frame.shared_target_candidates) == 1:
            return "pre_shared"
        if frame.recommended_binding_mode == "selective_per_unit":
            return "lazy"
        return "lazy" if binding_enabled else "skip"
