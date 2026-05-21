from __future__ import annotations

import re

from intent.types import ControlTrace, IntentAnalysis
from workflow.types import PowerName, WorkflowAction, WorkflowPlan, WorkflowPolicyFlags

_SCOPE_SWITCH_PATTERNS = (
    re.compile(r"另一个组"),
    re.compile(r"别的组"),
    re.compile(r"别的库"),
    re.compile(r"换(一个|别的)?(组|库)"),
    re.compile(r"不是这个(组|库)"),
)


def build_workflow_plan(
    analysis: IntentAnalysis,
    *,
    is_knowledge_query: bool,
    active_group_id: str | None = None,
    allowed_group_ids: tuple[str, ...] = (),
) -> WorkflowPlan:
    control = analysis.control
    trace = control.trace
    capabilities = set(control.capabilities)
    handling_mode = control.handling_mode
    route = control.route

    use_context = "use_context" in capabilities
    cite_sources = "cite_sources" in capabilities
    should_ask_clarification_first = handling_mode == "clarify"
    use_planner = _should_use_planner(route=route, trace=trace)
    decompose_query = _should_decompose_query(route=route, trace=trace)
    need_context_binding = _should_bind_context(use_context=use_context, trace=trace)
    rewrite_query = need_context_binding
    action = _resolve_action(
        route=route,
        handling_mode=handling_mode,
        is_knowledge_query=is_knowledge_query,
    )
    enabled_powers = _resolve_enabled_powers(
        route=route,
        handling_mode=handling_mode,
        use_planner=use_planner,
        decompose_query=decompose_query,
        is_knowledge_query=is_knowledge_query,
        need_context_binding=need_context_binding,
    )
    knowledge_scope_status = _resolve_knowledge_scope_status(
        query=analysis.input.user_query,
        active_group_id=active_group_id,
        allowed_group_ids=allowed_group_ids,
    )
    need_retrieval = is_knowledge_query and route in {"qa", "orchestrated"}
    policy_flags = WorkflowPolicyFlags(
        ask_clarification_first=should_ask_clarification_first or knowledge_scope_status == "needs_clarification",
        need_planner=use_planner,
        need_query_decomposition=decompose_query,
        need_context_binding=need_context_binding,
        need_retrieval=need_retrieval,
    )

    notes: list[str] = [
        f"route={route}",
        f"handling_mode={handling_mode}",
        f"knowledge_scope={knowledge_scope_status}",
    ]
    if is_knowledge_query:
        notes.append("knowledge_query")
    if use_planner:
        notes.append("planner_required")
    if decompose_query:
        notes.append("decompose_query")
    if rewrite_query:
        notes.append("bind_context")
    if should_ask_clarification_first:
        notes.append("clarify_before_execute")
    if need_retrieval:
        notes.append("retrieval_enabled")

    return WorkflowPlan(
        route=route,
        handling_mode=handling_mode,
        action=action,
        use_context=use_context,
        cite_sources=cite_sources,
        use_planner=use_planner,
        decompose_query=decompose_query,
        rewrite_query=rewrite_query,
        should_ask_clarification_first=should_ask_clarification_first,
        trace=trace,
        enabled_powers=enabled_powers,
        knowledge_scope_status=knowledge_scope_status,
        policy_flags=policy_flags,
        notes=tuple(notes),
    )


def _resolve_action(
    *,
    route: str,
    handling_mode: str,
    is_knowledge_query: bool,
) -> WorkflowAction:
    if route == "reject" or handling_mode == "unsupported":
        return "reject"
    if handling_mode in {"clarify", "scope_info"}:
        return "respond"
    if route == "chat":
        return "respond"
    if is_knowledge_query:
        return "knowledge_orchestrator"
    return "agent" if route in {"qa", "orchestrated"} else "respond"


def _should_use_planner(*, route: str, trace: ControlTrace) -> bool:
    if route != "orchestrated":
        return False
    if trace.task_topology == "staged":
        return True
    return trace.task_complexity == "complex" and trace.task_shape in {"compare", "mixed"}


def _should_decompose_query(*, route: str, trace: ControlTrace) -> bool:
    if route != "orchestrated":
        return False
    return trace.task_topology == "parallel_queries"


def _should_bind_context(*, use_context: bool, trace: ControlTrace) -> bool:
    if not use_context:
        return False
    return trace.context_dependency != "none" or bool(trace.ambiguity_states)


def _resolve_enabled_powers(
    *,
    route: str,
    handling_mode: str,
    use_planner: bool,
    decompose_query: bool,
    is_knowledge_query: bool,
    need_context_binding: bool,
) -> tuple[PowerName, ...]:
    if route == "reject" or handling_mode == "unsupported":
        return ()

    powers: list[PowerName] = []
    if need_context_binding:
        powers.append("context_binding_power")
    if is_knowledge_query and route in {"qa", "orchestrated"}:
        powers.append("retrieval_power")
    if handling_mode == "challenge" and route in {"qa", "orchestrated"}:
        powers.append("challenge_power")
    if use_planner and route == "orchestrated":
        powers.append("planning_power")
    if decompose_query and route == "orchestrated":
        powers.append("decomposition_power")
    if route == "chat":
        powers = [power for power in powers if power == "context_binding_power"]
    return tuple(dict.fromkeys(powers))


def _resolve_knowledge_scope_status(
    *,
    query: str,
    active_group_id: str | None,
    allowed_group_ids: tuple[str, ...],
) -> str:
    if not active_group_id:
        return "needs_clarification"
    if any(pattern.search(query) for pattern in _SCOPE_SWITCH_PATTERNS):
        explicit_groups = [group for group in allowed_group_ids if group and group in query]
        if explicit_groups:
            return "resolved"
        return "needs_clarification"
    return "resolved"
