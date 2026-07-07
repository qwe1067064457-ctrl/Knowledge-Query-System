from __future__ import annotations

from workflow.contracts.graph import ExecutionEdge, ExecutionGraph, ExecutionUnit, UnitResult
from workflow.orchestrated.execution_layer.runtime.langgraph_runtime import LangGraphExecutionRuntime


def _graph_with_synthesis() -> ExecutionGraph:
    return ExecutionGraph(
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


def test_parallel_group_runtime_runs_parallel_group_then_next_group() -> None:
    graph = _graph_with_synthesis()

    def build_node(unit_id: str):
        def _node(state):
            return {
                "unit_results": [UnitResult(unit_id=unit_id, capability="qa_like", state="completed")],
                "state_by_unit": {unit_id: "completed"},
                "evidence_bundles": [],
                "evidence_candidates": [],
                "key_events": [f"{unit_id}_done"],
                "preferred_binding_result": state.get("preferred_binding_result"),
            }

        return _node

    result = LangGraphExecutionRuntime().run(execution_graph=graph, build_node=build_node)

    assert [item.unit_id for item in result.unit_results] == ["u1", "u2", "u3"]
    assert result.key_events == ("u1_done", "u2_done", "u3_done")


def test_parallel_group_runtime_stops_on_clarification_block() -> None:
    graph = _graph_with_synthesis()

    def build_node(unit_id: str):
        def _node(state):
            result = UnitResult(
                unit_id=unit_id,
                capability="qa_like",
                state="blocked" if unit_id == "u1" else "completed",
                skipped_reason="binding_needs_clarification" if unit_id == "u1" else None,
            )
            return {
                "unit_results": [result],
                "state_by_unit": {unit_id: result.state},
                "evidence_bundles": [],
                "evidence_candidates": [],
                "key_events": [],
                "preferred_binding_result": state.get("preferred_binding_result"),
            }

        return _node

    result = LangGraphExecutionRuntime().run(execution_graph=graph, build_node=build_node)

    assert result.clarification_required is True
    assert "clarification_required" in result.key_events
    assert "u3" not in [item.unit_id for item in result.unit_results]


def test_parallel_group_runtime_retries_degraded_group_then_continues() -> None:
    graph = ExecutionGraph(
        units=(
            ExecutionUnit(unit_id="u1", goal="A", capability="qa_like").to_dict(),
            ExecutionUnit(unit_id="u2", goal="汇总", capability="synthesis", depends_on=("u1",)).to_dict(),
        ),
        edges=(ExecutionEdge(from_unit_id="u1", to_unit_id="u2").to_dict(),),
    )
    attempts = {"u1": 0}

    def build_node(unit_id: str):
        def _node(state):
            if unit_id == "u1":
                attempts["u1"] += 1
                unit_state = "degraded"
            else:
                unit_state = "completed"
            return {
                "unit_results": [UnitResult(unit_id=unit_id, capability="qa_like", state=unit_state)],
                "state_by_unit": {unit_id: unit_state},
                "evidence_bundles": [],
                "evidence_candidates": [],
                "key_events": [],
                "preferred_binding_result": state.get("preferred_binding_result"),
            }

        return _node

    result = LangGraphExecutionRuntime().run(execution_graph=graph, build_node=build_node)

    assert attempts["u1"] == 2
    assert result.degraded_units == ("u1",)
    assert [item.unit_id for item in result.unit_results] == ["u1", "u2"]
