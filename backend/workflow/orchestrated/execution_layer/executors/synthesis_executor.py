from memory_system.session_working_memory.models import SessionWorkingMemory
from workflow.orchestrated.execution_layer.contracts.unit_result import SynthesisResultPayload
from workflow.orchestrated.execution_layer.executors.registry import BaseCapabilityExecutor, CapabilityExecutionPlan


class SynthesisExecutor(BaseCapabilityExecutor):
    capability = "synthesis"

    def plan(self, *, unit, request, working_memory=None) -> CapabilityExecutionPlan:
        del request
        notes = ["synthesis_executor"]
        memory = working_memory if isinstance(working_memory, SessionWorkingMemory) else SessionWorkingMemory.from_dict(working_memory)
        consumed_answer_unit = any(entry.entry_type == "answer_unit" for entry in self._entries(memory))
        if consumed_answer_unit:
            notes.append("answer_unit_consumed")
        return CapabilityExecutionPlan(
            effective_goal=unit.goal,
            allow_retrieval=False,
            result_payload=SynthesisResultPayload(
                main_conclusion="",
                supporting_points=(),
                cautions=(),
                final_text_draft="",
                confidence="medium",
                consumed_working_memory=("answer_unit",) if consumed_answer_unit else (),
            ).to_dict(),
            notes=tuple(notes),
        )
