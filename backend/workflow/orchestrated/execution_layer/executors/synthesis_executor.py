from memory_system.session_working_memory.models import SessionWorkingMemory
from workflow.orchestrated.execution_layer.executors.registry import BaseCapabilityExecutor, CapabilityExecutionPlan


class SynthesisExecutor(BaseCapabilityExecutor):
    capability = "synthesis"

    def plan(self, *, unit, request, working_memory=None) -> CapabilityExecutionPlan:
        del request
        notes = ["synthesis_executor"]
        memory = working_memory if isinstance(working_memory, SessionWorkingMemory) else SessionWorkingMemory.from_dict(working_memory)
        if any(entry.entry_type == "answer_unit" for entry in self._entries(memory)):
            notes.append("answer_unit_consumed")
        return CapabilityExecutionPlan(
            effective_goal=unit.goal,
            allow_retrieval=False,
            notes=tuple(notes),
        )
