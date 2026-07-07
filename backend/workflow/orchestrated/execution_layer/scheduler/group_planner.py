from __future__ import annotations

from workflow.contracts.graph import ExecutionGraph


class ExecutionGroupPlanner:
    """Derive serial execution groups from graph dependencies."""

    def groups_for(self, execution_graph: ExecutionGraph) -> tuple[tuple[str, ...], ...]:
        units = {unit.unit_id: unit for unit in execution_graph.unit_objs() if unit.unit_id}
        if not units:
            return ()
        inbound: dict[str, set[str]] = {unit_id: set() for unit_id in units}
        outbound: dict[str, set[str]] = {unit_id: set() for unit_id in units}
        for edge in execution_graph.edge_objs():
            if edge.from_unit_id not in units or edge.to_unit_id not in units:
                continue
            inbound[edge.to_unit_id].add(edge.from_unit_id)
            outbound[edge.from_unit_id].add(edge.to_unit_id)
        unit_order = tuple(unit.unit_id for unit in execution_graph.unit_objs() if unit.unit_id)
        remaining = set(units)
        completed: set[str] = set()
        groups: list[tuple[str, ...]] = []
        while remaining:
            ready = tuple(
                unit_id
                for unit_id in unit_order
                if unit_id in remaining and inbound[unit_id].issubset(completed)
            )
            if not ready:
                raise ValueError("execution_group_cycle_or_unresolved_dependency")
            groups.append(ready)
            completed.update(ready)
            remaining.difference_update(ready)
        return tuple(groups)

    def notes_for_unit_groups(
        self,
        *,
        execution_graph: ExecutionGraph,
        expected_unit_groups: tuple[tuple[dict, ...], ...] = (),
    ) -> tuple[str, ...]:
        if not expected_unit_groups:
            return ()
        expected = tuple(tuple(str(unit.get("id") or unit.get("unit_id") or "") for unit in group) for group in expected_unit_groups)
        actual = self.groups_for(execution_graph)
        if expected == actual:
            return ()
        return ("unit_groups_conflict_graph_edges_graph_wins",)
