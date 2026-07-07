from memory_system.session_working_memory.models import SessionWorkingMemory
from workflow.orchestrated.execution_layer.contracts.unit_execution_outcome import UnitExecutionOutcome
from workflow.orchestrated.execution_layer.contracts.unit_result import VerifyResultPayload
from workflow.orchestrated.execution_layer.executors.base import BaseCapabilityExecutor
from workflow.runtime_skills.unit_runtime_config import tool_names_for_unit


class VerifyExecutor(BaseCapabilityExecutor):
    capability = "verify"
    worker_names = tool_names_for_unit(capability)

    def run(self, *, unit_context, worker_registry, llm_factory=None, trace_hooks=None) -> UnitExecutionOutcome:
        del trace_hooks
        notes = ["verify_executor"]
        memory = self._memory_from(unit_context.request.context.get("working_memory"))
        consumed_assertion = any(entry.entry_type == "user_assertion" for entry in self._entries(memory))
        if consumed_assertion:
            notes.append("user_assertion_consumed")

        binding_result = None
        if unit_context.binding_enabled and unit_context.unit.binding_mode != "skip" and worker_registry.has("target_resolution"):
            binding_result = worker_registry.get("target_resolution")(
                query=unit_context.unit.goal,
                candidates=unit_context.binding_candidates,
                working_memory=unit_context.request.context.get("working_memory"),
                recent_messages=unit_context.request.context.get("recent_messages"),
                llm_call=unit_context.request.context.get("bound_query_llm_call"),
                base_dir=str(unit_context.base_dir) if unit_context.base_dir else None,
                rewrite_query=True,
                recent_power=unit_context.recent_power,
                recent_object_type=unit_context.recent_object_type,
                memory_anchors=unit_context.request.context.get("memory_anchors"),
            )
        query_text = unit_context.unit.goal
        if binding_result is not None and worker_registry.has("query_rewrite"):
            query_text = worker_registry.get("query_rewrite")(
                query=unit_context.unit.goal,
                binding_result=binding_result.to_dict() if hasattr(binding_result, "to_dict") else dict(binding_result),
            )["query"]

        evidence_bundle = None
        evidence_candidates = ()
        key_events = []
        unit_state = "completed"
        skipped_reason = None
        if unit_context.allow_retrieval and unit_context.unit.retrieval_mode != "skip" and worker_registry.has("retrieval_execute"):
            query_units_payload = worker_registry.get("retrieval_query_builder")(
                unit_id=unit_context.unit.unit_id,
                query=query_text,
                target_refs=binding_result.target_refs() if binding_result is not None else (),
            )
            evidence_bundle = worker_registry.get("retrieval_execute")(query_units=query_units_payload["query_units"])
            bundle_view = worker_registry.get("retrieval_bundle")(evidence_bundle=evidence_bundle)
            evidence_candidates = tuple(bundle_view["evidence_candidates"])
            quality_view = worker_registry.get("retrieval_quality")(evidence_bundle=evidence_bundle)
            key_events.append("retrieval_performed")
            if str(quality_view.get("status", "unknown")) == "bad":
                key_events.append("retrieval_quality_weak")
                unit_state = "degraded"
                skipped_reason = "retrieval_quality_bad"

        payload = VerifyResultPayload(
            judgment="pending_verification",
            can_proceed=True,
            confidence="medium",
            summary=f"需要先验证: {query_text}",
            key_reasons=("verify_capability_selected",),
            consumed_working_memory=("user_assertion",) if consumed_assertion else (),
        ).to_dict()
        agent_result = self._invoke_agent_json(
            llm_factory=llm_factory,
            worker_registry=worker_registry,
            prompt_name="verify_react_prompt.md",
            payload={
                "query": query_text,
                "unit_id": unit_context.unit.unit_id,
                "goal": unit_context.unit.goal,
            },
        )
        if agent_result:
            payload.update({k: v for k, v in agent_result.items() if k in payload})
            notes.append("verify_react_agent")
        return UnitExecutionOutcome(
            unit_state=unit_state,
            result_payload=payload,
            notes=tuple(notes),
            key_events=tuple(key_events),
            binding_result=binding_result,
            evidence_bundle=evidence_bundle,
            evidence_candidates=evidence_candidates,
            skipped_reason=skipped_reason,
        )
