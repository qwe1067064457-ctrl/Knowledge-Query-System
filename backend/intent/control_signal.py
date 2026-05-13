from __future__ import annotations

from intent.types import ControlSignal, PlanningLevel, ResolvedIntent, ResolvedTask


def build_control_signal(
    resolved: ResolvedIntent,
    *,
    force_qa_citation: bool = True,
) -> ControlSignal:
    modifiers = resolved.modifiers
    task = resolved.task

    if resolved.main_intent == "unsupported" or modifiers.out_of_scope:
        return ControlSignal(route="reject", mode="clarify")

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

    if task.needs_agent_planning:
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
        decompose_query=task.needs_query_decomposition,
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
