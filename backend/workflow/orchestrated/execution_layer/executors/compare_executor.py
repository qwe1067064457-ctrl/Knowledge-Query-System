from memory_system.session_working_memory.models import SessionWorkingMemory
from workflow.orchestrated.execution_layer.contracts.unit_execution_outcome import UnitExecutionOutcome
from workflow.orchestrated.execution_layer.contracts.unit_result import CompareResultPayload
from workflow.orchestrated.execution_layer.executors.base import BaseCapabilityExecutor
from workflow.runtime_skills.unit_runtime_config import tool_names_for_unit


class CompareExecutor(BaseCapabilityExecutor):
    capability = "compare"
    worker_names = tool_names_for_unit(capability)

    def run(self, *, unit_context, worker_registry, llm_factory=None, trace_hooks=None) -> UnitExecutionOutcome:
        del trace_hooks
        notes = ["compare_executor"]
        consumed_focus_task = self._focus_task_hint(unit_context.request.context.get("working_memory"))
        if consumed_focus_task:
            notes.append("focus_task_consumed")
        evidence_bundle = None
        evidence_candidates = ()
        key_events = []
        if unit_context.allow_retrieval and unit_context.unit.retrieval_mode != "skip" and worker_registry.has("retrieval_execute"):
            query_units_payload = worker_registry.get("retrieval_query_builder")(
                unit_id=unit_context.unit.unit_id,
                query=unit_context.unit.goal,
                target_refs=(),
            )
            evidence_bundle = worker_registry.get("retrieval_execute")(query_units=query_units_payload["query_units"])
            bundle_view = worker_registry.get("retrieval_bundle")(evidence_bundle=evidence_bundle)
            evidence_candidates = tuple(bundle_view["evidence_candidates"])
            quality_view = worker_registry.get("retrieval_quality")(evidence_bundle=evidence_bundle)
            key_events.append("retrieval_performed")
            if str(quality_view.get("status", "unknown")) == "bad":
                key_events.append("retrieval_quality_weak")
        payload = CompareResultPayload(
            comparison_status="comparison_pending",
            summary=f"需要执行比较分析: {unit_context.unit.goal}",
            dimensions=(),
            tradeoff=(),
            confidence="medium",
            consumed_working_memory=("focus_task",) if consumed_focus_task else (),
        ).to_dict()
        agent_result = self._invoke_agent_json(
            llm_factory=llm_factory,
            worker_registry=worker_registry,
            prompt_name="compare_react_prompt.md",
            payload={
                "query": unit_context.unit.goal,
                "unit_id": unit_context.unit.unit_id,
            },
        )
        if agent_result:
            payload.update({k: v for k, v in agent_result.items() if k in payload})
            notes.append("compare_react_agent")
        return UnitExecutionOutcome(
            unit_state="completed",
            result_payload=payload,
            notes=tuple(notes),
            key_events=tuple(key_events),
            evidence_bundle=evidence_bundle,
            evidence_candidates=evidence_candidates,
        )

    def _focus_task_hint(self, working_memory) -> bool:
        memory = working_memory if isinstance(working_memory, SessionWorkingMemory) else SessionWorkingMemory.from_dict(working_memory)
        return any(entry.entry_type == "focus_task" for entry in self._entries(memory))
