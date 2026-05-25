from __future__ import annotations

from intent.schema.intent_types import ControlTrace, IntentModifiers
from workflow.retrieval_gate import RetrievalGate
from workflow.runners.base import RouteExecutionRequest
from workflow.types import WorkflowPlan, WorkflowPolicyFlags


def _make_plan(*, route: str = "qa", handling_mode: str = "normal", need_retrieval: bool = False) -> WorkflowPlan:
    return WorkflowPlan(
        route=route,
        handling_mode=handling_mode,
        action="agent",
        use_context=False,
        cite_sources=True,
        use_planner=False,
        decompose_query=False,
        rewrite_query=False,
        should_ask_clarification_first=False,
        trace=ControlTrace(
            main_intent="qa",
            modifiers=IntentModifiers(challenge=handling_mode == "challenge"),
            task_complexity="simple",
            task_shape="single_question",
            task_topology="single",
            context_dependency="none",
            ambiguity_states=(),
            missing_context_types=(),
            decision_strength="high",
            decision_source="test",
            decision_reason="test",
        ),
        enabled_powers=("retrieval_power",) if need_retrieval else (),
        knowledge_scope_status="resolved",
        policy_flags=WorkflowPolicyFlags(need_retrieval=need_retrieval),
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
