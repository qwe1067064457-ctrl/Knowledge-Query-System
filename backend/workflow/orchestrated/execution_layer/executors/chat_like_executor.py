from workflow.orchestrated.execution_layer.contracts.unit_execution_outcome import UnitExecutionOutcome
from workflow.orchestrated.execution_layer.executors.base import BaseCapabilityExecutor


class ChatLikeExecutor(BaseCapabilityExecutor):
    capability = "chat_like"
    worker_names = ()

    def run(self, *, unit_context, worker_registry, llm_factory=None, trace_hooks=None) -> UnitExecutionOutcome:
        del trace_hooks
        payload = {"summary": unit_context.unit.goal, "confidence": "medium"}
        notes = ["chat_like_executor"]
        agent_result = self._invoke_agent_json(
            llm_factory=llm_factory,
            worker_registry=worker_registry,
            prompt_name="chat_like_react_prompt.md",
            worker_names=self.worker_names,
            payload={
                "query": unit_context.unit.goal,
                "unit_id": unit_context.unit.unit_id,
            },
        )
        if agent_result:
            payload.update({k: v for k, v in agent_result.items() if k in payload})
            notes.append("chat_like_react_agent")
        return UnitExecutionOutcome(
            unit_state="completed",
            result_payload=payload,
            notes=tuple(notes),
        )
