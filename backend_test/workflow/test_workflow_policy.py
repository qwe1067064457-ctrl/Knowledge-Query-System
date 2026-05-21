from __future__ import annotations

from intent.types import (
    ContextState,
    ControlSignal,
    ControlTrace,
    DecisionTrace,
    IntentAnalysis,
    IntentInput,
    IntentModifiers,
    MainIntent,
    ResolvedIntent,
    ResolvedTask,
)
from workflow.policy import build_workflow_plan


def _make_analysis(
    *,
    query: str,
    route: str,
    handling_mode: str,
    capabilities: tuple[str, ...] = (),
    main_intent: MainIntent = "qa",
    task_complexity: str = "simple",
    task_shape: str = "single_question",
    task_topology: str = "single",
    context_dependency: str = "none",
    ambiguity_states: tuple[str, ...] = (),
    missing_context_types: tuple[str, ...] = (),
) -> IntentAnalysis:
    modifiers = IntentModifiers(challenge=handling_mode == "challenge")
    trace = ControlTrace(
        main_intent=main_intent,
        modifiers=modifiers,
        task_complexity=task_complexity,
        task_shape=task_shape,
        task_topology=task_topology,
        context_dependency=context_dependency,
        ambiguity_states=ambiguity_states,
        missing_context_types=missing_context_types,
        decision_strength="high",
        decision_source="rule",
        decision_reason="test",
    )
    return IntentAnalysis(
        input=IntentInput(user_query=query, context_state=ContextState()),
        evidence=None,  # type: ignore[arg-type]
        resolved=ResolvedIntent(
            main_intent=main_intent,
            modifiers=modifiers,
            task=ResolvedTask(
                complexity=task_complexity,
                shape=task_shape,
                topology=task_topology,
            ),
            context_dependency=context_dependency,
            decision=DecisionTrace(strength="high", source="rule", reason="test"),
        ),
        control=ControlSignal(
            route=route,
            handling_mode=handling_mode,
            capabilities=capabilities,  # type: ignore[arg-type]
            trace=trace,
        ),
    )


def test_orchestrated_plan_enables_planning_and_decomposition() -> None:
    analysis = _make_analysis(
        query="请比较A和B，并分别回答这两个问题？第二个问题是什么？",
        route="orchestrated",
        handling_mode="normal",
        capabilities=("cite_sources", "use_context"),
        task_complexity="complex",
        task_shape="compare",
        task_topology="parallel_queries",
        context_dependency="previous_answer",
    )

    plan = build_workflow_plan(
        analysis,
        is_knowledge_query=True,
        active_group_id="law",
        allowed_group_ids=("law", "medical"),
    )

    assert plan.route == "orchestrated"
    assert plan.use_planner is True
    assert plan.decompose_query is True
    assert plan.policy_flags.need_context_binding is True
    assert "retrieval_power" in plan.enabled_powers
    assert "planning_power" in plan.enabled_powers
    assert "decomposition_power" in plan.enabled_powers


def test_chat_plan_keeps_only_light_power() -> None:
    analysis = _make_analysis(
        query="那上面那个呢",
        route="chat",
        handling_mode="normal",
        capabilities=("use_context",),
        main_intent="chat",
        context_dependency="history_reference",
        ambiguity_states=("history_dependent",),
    )

    plan = build_workflow_plan(
        analysis,
        is_knowledge_query=False,
        active_group_id="general",
        allowed_group_ids=("general",),
    )

    assert plan.route == "chat"
    assert plan.enabled_powers == ("context_binding_power",)
    assert plan.use_planner is False
    assert plan.knowledge_scope_status == "resolved"


def test_scope_switch_without_explicit_group_requires_clarification() -> None:
    analysis = _make_analysis(
        query="查我另一个组里的制度",
        route="qa",
        handling_mode="normal",
        capabilities=("cite_sources",),
    )

    plan = build_workflow_plan(
        analysis,
        is_knowledge_query=True,
        active_group_id="law",
        allowed_group_ids=("law", "medical"),
    )

    assert plan.knowledge_scope_status == "needs_clarification"
    assert plan.policy_flags.ask_clarification_first is True
