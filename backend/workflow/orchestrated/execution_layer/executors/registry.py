from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from memory_system.session_working_memory.models import SessionWorkingMemory
from workflow.orchestrated.execution_layer.contracts.graph import ExecutionUnit, UnitState


@dataclass(frozen=True)
class CapabilityExecutionPlan:
    effective_goal: str
    allow_retrieval: bool = False
    terminal_state: UnitState | None = None
    terminal_reason: str | None = None
    result_payload: dict[str, Any] = None
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.result_payload is None:
            object.__setattr__(self, "result_payload", {})


class BaseCapabilityExecutor:
    capability = "qa_like"

    def plan(self, *, unit: ExecutionUnit, request, working_memory: SessionWorkingMemory | dict[str, Any] | None = None) -> CapabilityExecutionPlan:
        del request, working_memory
        return CapabilityExecutionPlan(effective_goal=unit.goal, allow_retrieval=unit.retrieval_mode != "skip")

    def _entries(self, memory: SessionWorkingMemory) -> list[object]:
        entries = memory.active_entries()
        return entries or memory.entries


from workflow.orchestrated.execution_layer.executors.qa_like_executor import QaLikeExecutor
from workflow.orchestrated.execution_layer.executors.chat_like_executor import ChatLikeExecutor
from workflow.orchestrated.execution_layer.executors.reject_like_executor import RejectLikeExecutor
from workflow.orchestrated.execution_layer.executors.compare_executor import CompareExecutor
from workflow.orchestrated.execution_layer.executors.verify_executor import VerifyExecutor
from workflow.orchestrated.execution_layer.executors.synthesis_executor import SynthesisExecutor


class CapabilityExecutorRegistry:
    def __init__(self) -> None:
        executors = (
            QaLikeExecutor(),
            ChatLikeExecutor(),
            RejectLikeExecutor(),
            CompareExecutor(),
            VerifyExecutor(),
            SynthesisExecutor(),
        )
        self._executors = {executor.capability: executor for executor in executors}

    def plan_for_unit(self, *, unit: ExecutionUnit, request, working_memory: SessionWorkingMemory | dict[str, Any] | None = None) -> CapabilityExecutionPlan:
        executor = self._executors.get(unit.capability, self._executors["qa_like"])
        return executor.plan(unit=unit, request=request, working_memory=working_memory)
