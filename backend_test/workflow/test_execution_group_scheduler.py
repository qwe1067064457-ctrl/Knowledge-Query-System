from __future__ import annotations

from workflow.contracts.graph import ExecutionEdge, ExecutionGraph, ExecutionUnit
from workflow.orchestrated.execution_layer.scheduler.group_planner import ExecutionGroupPlanner


def test_execution_group_planner_derives_topological_parallel_groups() -> None:
    graph = ExecutionGraph(
        units=(
            ExecutionUnit(unit_id="u1", goal="A", capability="qa_like").to_dict(),
            ExecutionUnit(unit_id="u2", goal="B", capability="verify").to_dict(),
            ExecutionUnit(unit_id="u3", goal="汇总", capability="synthesis", depends_on=("u1", "u2")).to_dict(),
        ),
        edges=(
            ExecutionEdge(from_unit_id="u1", to_unit_id="u3").to_dict(),
            ExecutionEdge(from_unit_id="u2", to_unit_id="u3").to_dict(),
        ),
    )

    groups = ExecutionGroupPlanner().groups_for(graph)

    assert groups == (("u1", "u2"), ("u3",))


def test_execution_group_planner_notes_when_planner_groups_conflict_with_graph_edges() -> None:
    graph = ExecutionGraph(
        units=(
            ExecutionUnit(unit_id="u1", goal="A", capability="qa_like").to_dict(),
            ExecutionUnit(unit_id="u2", goal="B", capability="synthesis", depends_on=("u1",)).to_dict(),
        ),
        edges=(ExecutionEdge(from_unit_id="u1", to_unit_id="u2").to_dict(),),
    )

    notes = ExecutionGroupPlanner().notes_for_unit_groups(
        execution_graph=graph,
        expected_unit_groups=(({"id": "u1"}, {"id": "u2"}),),
    )

    assert notes == ("unit_groups_conflict_graph_edges_graph_wins",)
