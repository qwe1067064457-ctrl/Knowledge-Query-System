from __future__ import annotations

from observability.runtime.run_factory import create_trace_context
from observability.runtime.trace_context_store import activate_trace_context
from workflow.contracts.graph import ExecutionGraph, ExecutionUnit, GlobalBindingFrame
from workflow.orchestrated.execution_layer.engine.execution_layer import ExecutionLayer
from workflow.runners.base import RouteExecutionRequest


def test_execution_layer_emits_workflow_run_event(workspace) -> None:
    worker = ExecutionLayer()
    graph = ExecutionGraph(
        units=(
            ExecutionUnit(
                unit_id="unit_primary",
                goal="展开这个结论",
                capability="qa_like",
                binding_mode="skip",
                output_slot="answer",
            ).to_dict(),
        ),
        edges=(),
    )
    request = RouteExecutionRequest(
        message="展开这个结论",
        messages=[{"role": "user", "content": "展开这个结论"}],
        context={},
    )
    trace_context = create_trace_context(
        session_id="session_workflow",
        group_id="law",
        user_id="u1",
    )

    with activate_trace_context(trace_context):
        result = worker.execute(
            execution_graph=graph,
            request=request,
            binding_candidates=[],
            global_binding_frame=GlobalBindingFrame(),
            binding_enable_flag=False,
            allow_retrieval=False,
        )

    assert result.unit_results[0].state == "completed"
    workflow_events = [item for item in trace_context.events if item.event_type == "workflow_run"]
    assert len(workflow_events) == 1
    assert workflow_events[0].metadata["workflow_name"] == "execution_layer"
    assert workflow_events[0].output_summary["unit_results"][0]["unit_id"] == "unit_primary"


def test_execution_layer_without_trace_context_keeps_business_result() -> None:
    worker = ExecutionLayer()
    graph = ExecutionGraph(
        units=(
            ExecutionUnit(
                unit_id="unit_primary",
                goal="直接回答",
                capability="qa_like",
                binding_mode="skip",
                output_slot="answer",
            ).to_dict(),
        ),
        edges=(),
    )
    request = RouteExecutionRequest(
        message="直接回答",
        messages=[{"role": "user", "content": "直接回答"}],
        context={},
    )

    result = worker.execute(
        execution_graph=graph,
        request=request,
        binding_candidates=[],
        global_binding_frame=GlobalBindingFrame(),
        binding_enable_flag=False,
        allow_retrieval=False,
    )

    assert result.unit_results[0].state == "completed"
