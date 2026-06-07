from workflow.orchestrated.execution_layer.contracts.unit_execution_outcome import UnitExecutionOutcome
from workflow.orchestrated.execution_layer.executors.base import BaseCapabilityExecutor


class RejectLikeExecutor(BaseCapabilityExecutor):
    capability = "reject_like"
    worker_names = ()

    def run(self, *, unit_context, worker_registry, llm_factory=None, trace_hooks=None) -> UnitExecutionOutcome:
        del trace_hooks
        payload = {"summary": unit_context.unit.goal, "confidence": "low"}
        notes = ["reject_like_executor"]
        skipped_reason = "reject_capability_selected"
        agent_result = self._invoke_agent_json(
            llm_factory=llm_factory,
            worker_registry=worker_registry,
            prompt_name="reject_like_react_prompt.md",
            worker_names=self.worker_names,
            payload={
                "query": unit_context.unit.goal,
                "unit_id": unit_context.unit.unit_id,
            },
        )
        if agent_result:
            payload.update({k: v for k, v in agent_result.items() if k in payload})
            skipped_reason = str(agent_result.get("skipped_reason") or skipped_reason)
            notes.append("reject_like_react_agent")
        return UnitExecutionOutcome(
            unit_state="blocked",
            result_payload=payload,
            notes=tuple(notes),
            skipped_reason=skipped_reason,
        )
