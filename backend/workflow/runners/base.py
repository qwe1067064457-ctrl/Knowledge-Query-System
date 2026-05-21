from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from workflow.types import ExecutionPayload, WorkflowPlan


@dataclass
class RouteExecutionRequest:
    message: str
    messages: list[dict[str, str]]
    is_knowledge_query: bool = False
    context: dict[str, Any] = field(default_factory=dict)


class BaseRouteRunner:
    route_name = "base"

    def run(self, plan: WorkflowPlan, request: RouteExecutionRequest) -> ExecutionPayload:
        return self._build_payload(plan, request, ())

    def _build_payload(
        self,
        plan: WorkflowPlan,
        request: RouteExecutionRequest,
        extra_instructions: tuple[str, ...],
        *,
        status: str = "ready",
    ) -> ExecutionPayload:
        instructions = list(extra_instructions)
        if plan.policy_flags.ask_clarification_first:
            instructions.append(
                "The current request is not ready for full execution yet. Ask a concise clarification question first and do not continue into a substantive answer."
            )
            if plan.trace.missing_context_types:
                missing = ", ".join(plan.trace.missing_context_types)
                instructions.append(f"Focus the clarification on these missing context types: {missing}.")
        if plan.handling_mode == "challenge":
            instructions.append(
                "Treat this as a challenge/correction turn. Re-evaluate the disputed point carefully, explain the basis, and avoid defending the previous answer blindly."
            )
        elif plan.handling_mode == "scope_info":
            instructions.append(
                "Treat this as a scope/capability question. Answer about what the system can or cannot do instead of executing the underlying task."
            )
        elif plan.handling_mode == "unsupported":
            instructions.append(
                "Treat this as an unsupported request. Refuse the operation briefly and, when possible, suggest a safer alternative."
            )

        if plan.use_planner:
            instructions.append("Use an internal lightweight plan before answering so the reasoning order is stable.")
        if plan.decompose_query:
            instructions.append("Cover each sub-question explicitly so no requested branch is skipped.")
        if plan.cite_sources:
            instructions.append("Provide supporting basis or citations when available, and make the grounding visible.")
        if plan.use_context:
            instructions.append("Use the current conversation context and do not treat this as a standalone fresh request.")
        if plan.knowledge_scope_status == "needs_clarification":
            instructions.append("The request implies switching knowledge scope, but the target group is unclear. Ask which knowledge group to search before retrieval.")
            status = "needs_clarification"

        return ExecutionPayload(
            route=plan.route,
            handling_mode=plan.handling_mode,
            action=plan.action,
            status=status,
            enabled_powers=plan.enabled_powers,
            instructions=tuple(instructions),
            knowledge_scope_status=plan.knowledge_scope_status,
            context_bundle={"trace": plan.trace.to_dict()},
            answer_constraints={
                "cite_sources": plan.cite_sources,
                "use_context": plan.use_context,
            },
            notes=plan.notes,
        )
