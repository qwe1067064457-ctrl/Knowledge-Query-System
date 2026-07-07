from __future__ import annotations

import re

from intent.schema.intent_types import ControlTrace, IntentAnalysis
from workflow.types import (
    PowerName,
    WorkflowAction,
    WorkflowHandlingMode,
    WorkflowPlan,
    WorkflowPolicyFlags,
    WorkflowRoute,
)

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
    route = _apply_admission_control(
        route=control.route,
        query=analysis.input.user_query,
        trace=trace,
    )

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
        capabilities=capabilities,
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
    route: WorkflowRoute,
    handling_mode: WorkflowHandlingMode,
    is_knowledge_query: bool,
    capabilities: set[str],
) -> WorkflowAction:
    del is_knowledge_query, capabilities
    if route == "reject" or handling_mode == "unsupported":
        return "reject"
    return "respond"


def _should_use_planner(*, route: WorkflowRoute, trace: ControlTrace) -> bool:
    if route != "orchestrated":
        return False
    if trace.task_topology == "staged":
        return True
    return trace.task_complexity == "complex" and trace.task_shape in {"compare", "mixed"}


def _should_decompose_query(*, route: WorkflowRoute, trace: ControlTrace) -> bool:
    if route != "orchestrated":
        return False
    return trace.task_topology == "parallel_queries"


def _apply_admission_control(
    *,
    route: WorkflowRoute,
    query: str,
    trace: ControlTrace,
) -> WorkflowRoute:
    if route != "orchestrated":
        return route
    if _requires_orchestrated(query=query, trace=trace):
        return route
    return "qa"


def _requires_orchestrated(*, query: str, trace: ControlTrace) -> bool:
    if trace.task_topology == "staged":
        return True
    if _has_explicit_parallel_markers(query):
        return True
    return trace.task_complexity == "complex" and trace.task_shape in {"compare", "mixed"}


def _has_explicit_parallel_markers(query: str) -> bool:
    normalized = str(query or "").strip()
    if not normalized:
        return False
    if len([part for part in re.split(r"[？?]\s*|\n+", normalized) if part.strip()]) > 1:
        return True
    return any(marker in normalized for marker in ("并且", "同时", "分别", "顺便", "另外", "再"))


def _should_bind_context(*, use_context: bool, trace: ControlTrace) -> bool:
    if not use_context:
        return False
    return trace.context_dependency != "none" or bool(trace.ambiguity_states)


def _resolve_enabled_powers(
    *,
    route: WorkflowRoute,
    handling_mode: WorkflowHandlingMode,
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
