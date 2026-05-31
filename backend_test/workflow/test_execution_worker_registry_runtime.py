from workflow.contracts.graph import ExecutionGraph, ExecutionUnit, GlobalBindingFrame
from workflow.orchestrated.execution_layer.engine.execution_layer import ExecutionLayer
from workflow.orchestrated.execution_layer.workers.base import BaseWorker
from workflow.orchestrated.execution_layer.workers.registry import WorkerRegistry
from workflow.runners.base import RouteExecutionRequest


class _EchoWorker(BaseWorker):
    name = "echo_worker"
    description = "Echo payload for registry tests."

    def run(self, value: str = ""):
        return {"value": value}


class _FakeBindingPower:
    def collect_candidates(self, entries, *, limit: int = 20):
        return list(entries)[:limit]

    def bind(self, query, candidates, **kwargs):
        del kwargs
        target = dict(candidates[0]) if candidates else {"object_id": "fallback", "content": query}

        class _Result:
            binding_ambiguous = False
            needs_clarification = False
            rewritten_query = f"{target.get('content', '')} {query}".strip()

            def to_dict(self):
                return {
                    "rewritten_query": self.rewritten_query,
                    "bound_targets": [target],
                }

            def target_refs(self):
                return (str(target.get("object_id") or ""),)

        return _Result()


def test_worker_registry_registers_and_resolves_worker() -> None:
    registry = WorkerRegistry()
    registry.register(_EchoWorker())

    assert registry.has("echo_worker") is True
    assert registry.get("echo_worker")(value="ok") == {"value": "ok"}


def test_worker_registry_reports_missing_worker() -> None:
    registry = WorkerRegistry()

    assert registry.has("missing_worker") is False


def test_execution_layer_builds_compat_binding_workers_from_power() -> None:
    worker = ExecutionLayer()
    graph = ExecutionGraph(
        units=(
            ExecutionUnit(
                unit_id="unit_primary",
                goal="展开这个结论",
                capability="qa_like",
                binding_mode="lazy",
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

    result = worker.execute(
        execution_graph=graph,
        request=request,
        binding_candidates=[{"object_id": "question_1", "content": "这个结论"}],
        global_binding_frame=GlobalBindingFrame(
            query_is_context_dependent=True,
            binding_scope_hint="partial",
            shared_target_candidates=("question_1",),
            recommended_binding_mode="selective_per_unit",
        ),
        context_binding_power=_FakeBindingPower(),
        binding_enable_flag=True,
    )

    assert result.unit_results[0].used_binding is True
    assert "这个结论" in str(result.unit_results[0].result_payload.get("summary", ""))


def test_execution_layer_compat_registry_stays_empty_without_power_or_worker_registry() -> None:
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

    assert result.unit_results[0].used_binding is False
    assert result.evidence_bundle is None
