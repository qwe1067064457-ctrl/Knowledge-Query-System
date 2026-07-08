from workflow.orchestrated.execution_layer.contracts.unit_execution_outcome import UnitExecutionOutcome
from workflow.orchestrated.execution_layer.executors.base import BaseCapabilityExecutor
from workflow.runtime_skills.unit_runtime_config import tool_names_for_unit


class QaLikeExecutor(BaseCapabilityExecutor):
    capability = "qa_like"
    worker_names = tool_names_for_unit(capability)

    def run(self, *, unit_context, worker_registry, llm_factory=None, trace_hooks=None) -> UnitExecutionOutcome:
        del trace_hooks
        binding_result = None
        if unit_context.binding_enabled and unit_context.unit.binding_mode != "skip" and worker_registry.has("target_resolution"):
            candidate_entries = unit_context.binding_candidates
            if unit_context.unit.binding_mode == "pre_shared":
                wanted = set(unit_context.global_binding_frame.shared_target_candidates)
                candidate_entries = [
                    item
                    for item in unit_context.binding_candidates
                    if str(item.get("object_id") or item.get("content") or "").strip() in wanted
                ]
            binding_result = worker_registry.get("target_resolution")(
                query=unit_context.unit.goal,
                candidates=candidate_entries,
                working_memory=unit_context.request.context.get("working_memory"),
                recent_messages=unit_context.request.context.get("recent_messages"),
                llm_call=unit_context.request.context.get("bound_query_llm_call"),
                base_dir=str(unit_context.base_dir) if unit_context.base_dir else None,
                rewrite_query=True,
                recent_power=unit_context.recent_power,
                recent_object_type=unit_context.recent_object_type,
                memory_anchors=unit_context.request.context.get("memory_anchors"),
            )
            if getattr(binding_result, "needs_clarification", False):
                return UnitExecutionOutcome(
                    unit_state="blocked",
                    result_payload={"summary": unit_context.unit.goal, "confidence": "low"},
                    notes=("qa_like_executor",),
                    key_events=("binding_needs_clarification",),
                    binding_result=binding_result,
                    skipped_reason="binding_needs_clarification",
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
        agent_result = self._invoke_agent_json(
            llm_factory=llm_factory,
            worker_registry=worker_registry,
            prompt_name="qa_like_react_prompt.md",
            payload={
                "query": query_text,
                "unit_id": unit_context.unit.unit_id,
                "goal": unit_context.unit.goal,
            },
        )
        payload = {"summary": query_text, "confidence": "medium"}
        notes = ["qa_like_executor"]
        if agent_result:
            payload.update({k: v for k, v in agent_result.items() if k in payload})
            notes.append("qa_like_react_agent")
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
