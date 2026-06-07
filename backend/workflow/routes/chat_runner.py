from __future__ import annotations

from dataclasses import replace

from workflow.routes.base import BaseRouteRunner, RouteExecutionRequest
from workflow.powers.context_binding_power import ContextBindingPower
from workflow.types import ContextBindingResult, WorkflowPlan


def _merge_key_events(*event_groups: tuple[str, ...] | list[str]) -> tuple[str, ...]:
    merged: list[str] = []
    for group in event_groups:
        for item in group:
            if item and item not in merged:
                merged.append(str(item))
    return tuple(merged)


def _binding_events(binding: ContextBindingResult | None) -> tuple[str, ...]:
    if binding is None:
        return ()
    if binding.needs_clarification:
        return ("clarification_required", "binding_ambiguous")
    return ("binding_ambiguous",) if binding.binding_ambiguous else ("binding_applied",)


class ChatRouteRunner(BaseRouteRunner):
    route_name = "chat"

    def __init__(self) -> None:
        self.context_binding_power = ContextBindingPower()

    def run(self, plan: WorkflowPlan, request: RouteExecutionRequest):
        payload = self._build_payload(
            plan,
            request,
            ("This is a chat turn. Respond naturally and do not over-structure the answer.",),
        )
        context_bundle = payload.context_bundle_obj()
        key_events: tuple[str, ...] = ()

        if "context_binding_power" in plan.enabled_powers:
            candidate_entries = self.context_binding_power.collect_candidates(
                self._registry_binding_candidates(request)
            )
            binding_result = self.context_binding_power.bind(
                request.message,
                candidate_entries,
                working_memory=request.context.get("working_memory"),
                recent_messages=list(request.messages or ())[-6:],
                llm_call=request.context.get("bound_query_llm_call"),
                base_dir=request.context.get("base_dir"),
                rewrite_query=bool(plan.rewrite_query),
                recent_power=request.context.get("recent_power"),
                recent_object_type=request.context.get("recent_object_type"),
                memory_anchors=request.context.get("memory_anchors"),
            )
            context_bundle = replace(
                context_bundle,
                binding=binding_result,
                binding_summary=binding_result.binding_summary or "binding_applied",
                candidate_count=len(candidate_entries),
            )
            key_events = _merge_key_events(key_events, _binding_events(binding_result))
            if binding_result.needs_clarification and payload.status == "ready":
                payload = replace(payload, status="needs_clarification")

        return self._finalize_payload(
            payload,
            plan,
            context_bundle=context_bundle,
            key_events=key_events,
        )
