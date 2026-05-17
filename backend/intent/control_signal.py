from __future__ import annotations

from intent.task_compat import build_task_compat
from intent.types import ControlSignal, PlanningLevel, ResolvedIntent, ResolvedTask


def build_control_signal(
    resolved: ResolvedIntent,
    *,
    force_qa_citation: bool = True,
) -> ControlSignal:
    modifiers = resolved.modifiers
    task = resolved.task
    compat = build_task_compat(task)

    if resolved.main_intent == "unsupported" or modifiers.out_of_scope:
        return ControlSignal(route="reject", mode="clarify")

    if _should_rescue_complex_qa_route(resolved):
        planning_level = _planning_level_for_task(task)
        return ControlSignal(
            route="agent",
            mode="normal",
            rewrite=True,
            force_citation=force_qa_citation or modifiers.ask_source,
            use_planner=planning_level == "full",
            decompose_query=False,
            planning_level=planning_level,
        )

    if modifiers.needs_clarification:
        return ControlSignal(route="direct", mode="clarify")

    if resolved.main_intent == "system" or modifiers.ask_capability:
        return ControlSignal(route="direct", mode="capability")

    if resolved.main_intent == "chat":
        return ControlSignal(route="chat", mode="normal")

    if modifiers.challenge:
        return ControlSignal(
            route="rag",
            mode="challenge",
            rewrite=True,
            force_citation=True,
            use_planner=False,
            decompose_query=False,
            planning_level="none",
        )

    if compat.needs_agent_planning:
        planning_level = _planning_level_for_task(task)
        return ControlSignal(
            route="agent",
            mode="normal",
            rewrite=modifiers.follow_up or resolved.context_dependency != "none",
            force_citation=force_qa_citation,
            use_planner=planning_level == "full",
            decompose_query=False,
            planning_level=planning_level,
        )

    return ControlSignal(
        route="rag",
        mode="normal",
        rewrite=modifiers.follow_up or resolved.context_dependency != "none",
        force_citation=force_qa_citation or modifiers.ask_source,
        use_planner=False,
        decompose_query=compat.needs_query_decomposition,
        planning_level="none",
    )


def _planning_level_for_task(task: ResolvedTask) -> PlanningLevel:
    if task.complexity != "complex":
        return "none"
    if task.shape in {"compare", "mixed"}:
        return "full"
    if task.shape in {"verify", "extract"}:
        return "light"
    return "none"


def _should_rescue_complex_qa_route(resolved: ResolvedIntent) -> bool:
    if resolved.main_intent != "qa" or not resolved.modifiers.needs_clarification:
        return False
    task = resolved.task
    return task.complexity == "complex" and task.shape in {"verify", "compare", "mixed"}
