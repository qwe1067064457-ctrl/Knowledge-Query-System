from memory_system.session_working_memory.models import SessionWorkingMemory
from workflow.orchestrated.execution_layer.contracts.unit_result import VerifyResultPayload
from workflow.orchestrated.execution_layer.executors.registry import BaseCapabilityExecutor, CapabilityExecutionPlan


class VerifyExecutor(BaseCapabilityExecutor):
    capability = "verify"

    def plan(self, *, unit, request, working_memory=None) -> CapabilityExecutionPlan:
        del request
        notes = ["verify_executor"]
        memory = working_memory if isinstance(working_memory, SessionWorkingMemory) else SessionWorkingMemory.from_dict(working_memory)
        consumed_assertion = any(entry.entry_type == "user_assertion" for entry in self._entries(memory))
        if consumed_assertion:
            notes.append("user_assertion_consumed")
        return CapabilityExecutionPlan(
            effective_goal=unit.goal,
            allow_retrieval=unit.retrieval_mode != "skip",
            result_payload=VerifyResultPayload(
                judgment="pending_verification",
                can_proceed=True,
                confidence="medium",
                summary=f"需要先验证: {unit.goal}",
                key_reasons=("verify_capability_selected",),
                consumed_working_memory=("user_assertion",) if consumed_assertion else (),
            ).to_dict(),
            notes=tuple(notes),
        )
