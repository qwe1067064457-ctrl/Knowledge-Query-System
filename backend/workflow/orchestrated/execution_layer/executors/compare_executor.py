from memory_system.session_working_memory.models import SessionWorkingMemory
from workflow.orchestrated.execution_layer.contracts.unit_result import CompareResultPayload
from workflow.orchestrated.execution_layer.executors.registry import BaseCapabilityExecutor, CapabilityExecutionPlan


class CompareExecutor(BaseCapabilityExecutor):
    capability = "compare"

    def plan(self, *, unit, request, working_memory=None) -> CapabilityExecutionPlan:
        del request
        notes = ["compare_executor"]
        consumed_focus_task = self._focus_task_hint(working_memory)
        if consumed_focus_task:
            notes.append("focus_task_consumed")
        return CapabilityExecutionPlan(
            effective_goal=unit.goal,
            allow_retrieval=unit.retrieval_mode != "skip",
            result_payload=CompareResultPayload(
                comparison_status="comparison_pending",
                summary=f"需要执行比较分析: {unit.goal}",
                dimensions=(),
                tradeoff=(),
                confidence="medium",
                consumed_working_memory=("focus_task",) if consumed_focus_task else (),
            ).to_dict(),
            notes=tuple(notes),
        )

    def _focus_task_hint(self, working_memory) -> bool:
        memory = working_memory if isinstance(working_memory, SessionWorkingMemory) else SessionWorkingMemory.from_dict(working_memory)
        return any(entry.entry_type == "focus_task" for entry in self._entries(memory))
