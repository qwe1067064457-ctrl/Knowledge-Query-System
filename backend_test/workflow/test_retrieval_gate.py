from __future__ import annotations

from intent.schema.intent_types import ControlTrace, IntentModifiers
from workflow.retrieval_gate import RetrievalGate
from workflow.runners.base import RouteExecutionRequest
from workflow.types import WorkflowHandlingMode, WorkflowPlan, WorkflowPolicyFlags, WorkflowRoute


def _make_plan(
    *,
    route: WorkflowRoute = "qa",
    handling_mode: WorkflowHandlingMode = "normal",
    need_retrieval: bool = False,
    use_context: bool = False,
    need_context_binding: bool = False,
) -> WorkflowPlan:
    return WorkflowPlan(
        route=route,
        handling_mode=handling_mode,
        action="respond",
        use_context=use_context,
        cite_sources=True,
        use_planner=False,
        decompose_query=False,
        rewrite_query=use_context,
        should_ask_clarification_first=False,
        trace=ControlTrace(
            main_intent="qa",
            modifiers=IntentModifiers(challenge=handling_mode == "challenge"),
            task_complexity="simple",
            task_shape="single_question",
            task_topology="single",
            context_dependency="previous_answer" if use_context else "none",
            ambiguity_states=("history_dependent",) if use_context else (),
            missing_context_types=(),
            decision_strength="high",
            decision_source="test",
            decision_reason="test",
        ),
        enabled_powers=("retrieval_power",) if need_retrieval else (),
        knowledge_scope_status="resolved",
        policy_flags=WorkflowPolicyFlags(
            need_retrieval=need_retrieval,
            need_context_binding=need_context_binding,
        ),
        notes=("test",),
    )


def test_retrieval_gate_requests_retrieval_for_knowledge_query() -> None:
    gate = RetrievalGate()
    plan = _make_plan(need_retrieval=True)
    request = RouteExecutionRequest(
        message="劳动合同法第19条怎么规定？",
        messages=[{"role": "user", "content": "劳动合同法第19条怎么规定？"}],
        is_knowledge_query=True,
    )

    decision = gate.decide(plan=plan, request=request)

    assert decision.should_retrieve is True
    assert decision.reason == "knowledge_query"


def test_retrieval_gate_skips_retrieval_for_context_answer() -> None:
    gate = RetrievalGate()
    plan = _make_plan(need_retrieval=False)
    request = RouteExecutionRequest(
        message="把你刚才那句话再说简单一点",
        messages=[{"role": "user", "content": "把你刚才那句话再说简单一点"}],
        is_knowledge_query=False,
    )

    decision = gate.decide(plan=plan, request=request)

    assert decision.should_retrieve is False
    assert decision.reason == "context_answer_ok"


def test_retrieval_gate_marks_memory_hit_that_needs_hydration() -> None:
    gate = RetrievalGate()
    plan = _make_plan(use_context=True, need_context_binding=True)
    request = RouteExecutionRequest(
        message="那个案例后来怎么收口的？",
        messages=[{"role": "user", "content": "那个案例后来怎么收口的？"}],
        is_knowledge_query=False,
        context={
            "memory_anchors": [
                {
                    "memory_type": "daily_log",
                    "source_session_id": "session_older",
                    "summary": "之前讨论过一个案例。",
                }
            ],
            "memory_anchor_summary_sufficient": False,
        },
    )

    decision = gate.decide(plan=plan, request=request)

    assert decision.reason == "memory_hit_needs_hydrate"
    assert decision.use_memory_first is True
    assert decision.should_retrieve is False
    assert decision.should_rewrite is True


def test_retrieval_gate_keeps_context_answer_when_memory_summary_already_sufficient() -> None:
    gate = RetrievalGate()
    plan = _make_plan(use_context=True, need_context_binding=True)
    request = RouteExecutionRequest(
        message="把刚才那段总结再收一下",
        messages=[{"role": "user", "content": "把刚才那段总结再收一下"}],
        is_knowledge_query=False,
        context={
            "memory_anchors": [
                {
                    "memory_type": "daily_log",
                    "source_session_id": "session_older",
                    "summary": "之前讨论过一个案例。",
                }
            ],
            "memory_anchor_summary_sufficient": True,
        },
    )

    decision = gate.decide(plan=plan, request=request)

    assert decision.reason == "context_answer_ok"
    assert decision.should_retrieve is False


def test_retrieval_gate_keeps_challenge_reason_when_memory_is_already_hydrated() -> None:
    gate = RetrievalGate()
    plan = _make_plan(handling_mode="challenge", need_retrieval=True, use_context=True, need_context_binding=True)
    request = RouteExecutionRequest(
        message="你刚才这个依据真的够吗？",
        messages=[{"role": "user", "content": "你刚才这个依据真的够吗？"}],
        is_knowledge_query=False,
        context={
            "memory_anchors": [
                {
                    "memory_type": "daily_log",
                    "source_session_id": "session_older",
                    "summary": "之前讨论过一个案例。",
                }
            ],
            "hydrated_memory_context": [{"id": "entry_1", "role": "assistant", "content": "历史回答"}],
        },
    )

    decision = gate.decide(plan=plan, request=request)

    assert decision.reason == "challenge_turn"
    assert decision.should_retrieve is True
