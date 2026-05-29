from memory_system.session_working_memory.models import SessionWorkingMemory
from workflow.orchestrated.execution_layer.executors.registry import BaseCapabilityExecutor, CapabilityExecutionPlan


class VerifyExecutor(BaseCapabilityExecutor):
    capability = "verify"

    def plan(self, *, unit, request, working_memory=None) -> CapabilityExecutionPlan:
        del request
        notes = ["verify_executor"]
        memory = working_memory if isinstance(working_memory, SessionWorkingMemory) else SessionWorkingMemory.from_dict(working_memory)
        if any(entry.entry_type == "user_assertion" for entry in self._entries(memory)):
            notes.append("user_assertion_consumed")
        return CapabilityExecutionPlan(
            effective_goal=unit.goal,
            allow_retrieval=unit.retrieval_mode != "skip",
            notes=tuple(notes),
        )
