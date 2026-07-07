from __future__ import annotations

from intent.schema.intent_types import (
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
from workflow.types import WorkflowHandlingMode, WorkflowRoute


def _make_analysis(
    *,
    query: str,
    route: WorkflowRoute,
    handling_mode: WorkflowHandlingMode,
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
    assert plan.action == "respond"


def test_reject_plan_does_not_enable_any_power() -> None:
    analysis = _make_analysis(
        query="执行这个不支持的操作",
        route="reject",
        handling_mode="unsupported",
        capabilities=("use_context", "cite_sources"),
        main_intent="unsupported",
        context_dependency="history_reference",
        ambiguity_states=("history_dependent",),
    )

    plan = build_workflow_plan(
        analysis,
        is_knowledge_query=False,
        active_group_id="general",
        allowed_group_ids=("general",),
    )

    assert plan.route == "reject"
    assert plan.enabled_powers == ()
    assert plan.action == "reject"


def test_non_knowledge_qa_defaults_to_respond_instead_of_agent() -> None:
    analysis = _make_analysis(
        query="把上一个结论展开讲讲",
        route="qa",
        handling_mode="normal",
        capabilities=("use_context",),
        context_dependency="previous_answer",
        ambiguity_states=("history_dependent",),
    )

    plan = build_workflow_plan(
        analysis,
        is_knowledge_query=False,
        active_group_id="general",
        allowed_group_ids=("general",),
    )

    assert plan.route == "qa"
    assert plan.action == "respond"


def test_non_knowledge_orchestrated_defaults_to_respond_instead_of_agent() -> None:
    analysis = _make_analysis(
        query="先比较 A 和 B，再给一个结论",
        route="orchestrated",
        handling_mode="normal",
        capabilities=("cite_sources",),
        task_complexity="complex",
        task_shape="compare",
        task_topology="parallel_queries",
    )

    plan = build_workflow_plan(
        analysis,
        is_knowledge_query=False,
        active_group_id="general",
        allowed_group_ids=("general",),
    )

    assert plan.route == "orchestrated"
    assert plan.action == "respond"


def test_unknown_capability_does_not_change_workflow_action() -> None:
    analysis = _make_analysis(
        query="先看这个，再决定怎么操作",
        route="qa",
        handling_mode="normal",
        capabilities=("unknown_capability",),
    )

    plan = build_workflow_plan(
        analysis,
        is_knowledge_query=False,
        active_group_id="general",
        allowed_group_ids=("general",),
    )

    assert plan.route == "qa"
    assert plan.action == "respond"


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


def test_knowledge_query_stays_on_workflow_respond_path() -> None:
    analysis = _make_analysis(
        query="试用期依据是什么",
        route="qa",
        handling_mode="normal",
        capabilities=("cite_sources",),
    )

    plan = build_workflow_plan(
        analysis,
        is_knowledge_query=True,
        active_group_id="law",
        allowed_group_ids=("law",),
    )

    assert plan.route == "qa"
    assert plan.action == "respond"


def test_workflow_plan_keeps_string_contract_and_follow_up_stays_outside_handling_mode() -> None:
    analysis = _make_analysis(
        query="把你刚才第二点展开讲讲",
        route="qa",
        handling_mode="normal",
        capabilities=("use_context",),
        context_dependency="previous_answer",
        ambiguity_states=("history_dependent",),
    )

    plan = build_workflow_plan(
        analysis,
        is_knowledge_query=False,
        active_group_id="general",
        allowed_group_ids=("general",),
    )

    payload = plan.to_dict()

    assert payload["route"] == "qa"
    assert isinstance(payload["route"], str)
    assert payload["handling_mode"] == "normal"
    assert isinstance(payload["handling_mode"], str)
    assert plan.policy_flags.need_context_binding is True
    assert "context_binding_power" in plan.enabled_powers
