from __future__ import annotations

from memory_system.session_working_memory.models import SessionWorkingMemory
from workflow.contracts.graph import ExecutionUnit
from workflow.orchestrated.execution_layer.executors.base import BaseCapabilityExecutor
from workflow.orchestrated.execution_layer.executors.chat_like_executor import ChatLikeExecutor
from workflow.orchestrated.execution_layer.executors.compare_executor import CompareExecutor
from workflow.orchestrated.execution_layer.executors.qa_like_executor import QaLikeExecutor
from workflow.orchestrated.execution_layer.executors.reject_like_executor import RejectLikeExecutor
from workflow.orchestrated.execution_layer.executors.synthesis_executor import SynthesisExecutor
from workflow.orchestrated.execution_layer.executors.verify_executor import VerifyExecutor


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

    def executor_for(
        self,
        *,
        unit: ExecutionUnit,
        request,
        working_memory: SessionWorkingMemory | dict | None = None,
    ) -> BaseCapabilityExecutor:
        del request, working_memory
        return self._executors.get(unit.capability, self._executors["qa_like"])
