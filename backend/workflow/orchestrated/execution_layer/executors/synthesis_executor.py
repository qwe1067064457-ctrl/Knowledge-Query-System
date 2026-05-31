from memory_system.session_working_memory.models import SessionWorkingMemory
from workflow.orchestrated.execution_layer.contracts.unit_execution_outcome import UnitExecutionOutcome
from workflow.orchestrated.execution_layer.contracts.unit_result import SynthesisResultPayload
from workflow.orchestrated.execution_layer.executors.base import BaseCapabilityExecutor


class SynthesisExecutor(BaseCapabilityExecutor):
    capability = "synthesis"
    worker_names = (
        "finding_projection",
        "evidence_anchor",
        "caution_assembly",
    )

    def run(self, *, unit_context, worker_registry, llm_factory=None, trace_hooks=None) -> UnitExecutionOutcome:
        del trace_hooks
        notes = ["synthesis_executor"]
        memory = self._memory_from(unit_context.request.context.get("working_memory"))
        consumed_answer_unit = any(entry.entry_type == "answer_unit" for entry in self._entries(memory))
        if consumed_answer_unit:
            notes.append("answer_unit_consumed")
        payload = SynthesisResultPayload(
            main_conclusion=f"需要整合前序结果: {unit_context.unit.goal}",
            supporting_points=(),
            cautions=(),
            final_text_draft="",
            confidence="medium",
            consumed_working_memory=("answer_unit",) if consumed_answer_unit else (),
        ).to_dict()
        agent_result = self._invoke_agent_json(
            llm_factory=llm_factory,
            worker_registry=worker_registry,
            prompt_name="synthesis_react_prompt.md",
            worker_names=self.worker_names,
            payload={
                "query": unit_context.unit.goal,
                "unit_id": unit_context.unit.unit_id,
            },
        )
        if agent_result:
            payload.update({k: v for k, v in agent_result.items() if k in payload})
            notes.append("synthesis_react_agent")
        return UnitExecutionOutcome(
            unit_state="completed",
            result_payload=payload,
            notes=tuple(notes),
        )
