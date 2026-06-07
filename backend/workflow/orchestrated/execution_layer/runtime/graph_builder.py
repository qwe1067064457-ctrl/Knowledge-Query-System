from __future__ import annotations

from typing import Callable

from langgraph.graph import END, START, StateGraph

from workflow.contracts.graph import ExecutionGraph
from workflow.orchestrated.execution_layer.runtime.state import ExecutionRuntimeState


class LangGraphExecutionGraphBuilder:
    def build(
        self,
        *,
        execution_graph: ExecutionGraph,
        node_factory: Callable[[str], Callable[[ExecutionRuntimeState], dict]],
    ):
        graph = StateGraph(ExecutionRuntimeState)
        entry_units = set(execution_graph.entry_unit_ids())
        outbound: dict[str, list[str]] = {}

        for unit in execution_graph.unit_objs():
            graph.add_node(unit.unit_id, node_factory(unit.unit_id))

        for edge in execution_graph.edge_objs():
            outbound.setdefault(edge.from_unit_id, []).append(edge.to_unit_id)
            graph.add_edge(edge.from_unit_id, edge.to_unit_id)

        for unit in execution_graph.unit_objs():
            if unit.unit_id in entry_units:
                graph.add_edge(START, unit.unit_id)
            if unit.unit_id not in outbound:
                graph.add_edge(unit.unit_id, END)

        return graph.compile()

