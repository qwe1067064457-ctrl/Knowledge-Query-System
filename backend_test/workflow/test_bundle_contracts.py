from __future__ import annotations

from intent.schema.intent_types import ControlTrace, IntentModifiers
from workflow.runners.base import BaseRouteRunner
from workflow.types import ContextBundle, PlanBundle, ReviewBundle, WorkflowPlan, WorkflowPolicyFlags


class _DummyRunner(BaseRouteRunner):
    route_name = "dummy"


def _make_plan() -> WorkflowPlan:
    trace = ControlTrace(
        main_intent="qa",
        modifiers=IntentModifiers(),
        task_complexity="simple",
        task_shape="single_question",
        task_topology="single",
        context_dependency="none",
        ambiguity_states=(),
        missing_context_types=(),
        decision_strength="high",
        decision_source="rule",
        decision_reason="test",
    )
    return WorkflowPlan(
        route="qa",
        handling_mode="normal",
        action="respond",
        use_context=False,
        cite_sources=False,
        use_planner=False,
        decompose_query=False,
        rewrite_query=False,
        should_ask_clarification_first=False,
        trace=trace,
        enabled_powers=(),
        knowledge_scope_status="resolved",
        policy_flags=WorkflowPolicyFlags(),
        notes=(),
    )


def test_bundle_types_preserve_positive_contract() -> None:
    context = ContextBundle.from_dict(
        {
            "trace": {"main_intent": "qa"},
            "binding": {"bound_targets": [{"ref": "claim_1"}]},
            "binding_summary": "pattern_match",
            "candidate_count": 2,
            "query_units": [{"unit_id": "q1", "text": "foo"}],
        }
    ).to_dict()
    plan = PlanBundle.from_dict(
        {
            "goal": "比较A和B",
            "task_shape": "compare",
            "task_topology": "parallel_queries",
            "planning_mode": "compare",
            "ordered_steps": [{"title": "Compare", "sequence": 1}],
            "comparison_units": [{"left": "A", "right": "B"}],
            "execution_checkpoints": [{"name": "coverage"}],
            "bound_target_refs": ["compare_1"],
            "refined": True,
            "fallback_used": False,
            "fallback_reason": [],
        }
    ).to_dict()
    review = ReviewBundle.from_dict(
        {
            "review_mode": "challenge_review",
            "review_confidence": "medium",
            "review_scope": "multi_target",
            "status": "partial_success",
            "targets": [{"target_ref": "claim_1"}, {"target_ref": "claim_2"}],
            "evidence_assessment": {"partially_sufficient": True},
            "review_findings": [{"target_ref": "claim_1", "judgment": "supported"}],
            "review_summary": {
                "matched_target_count": 1,
                "matched_target_refs": ["claim_1"],
                "unsupported_target_refs": ["claim_2"],
                "needs_more_evidence_targets": ["claim_2"],
            },
        }
    ).to_dict()

    assert context["binding_summary"] == "pattern_match"
    assert context["candidate_count"] == 2
    assert context["query_units"][0]["unit_id"] == "q1"
    assert plan["plan_summary"]["planning_mode"] == "compare"
    assert plan["plan_summary"]["step_count"] == 1
    assert plan["plan_summary"]["bound_target_ref_count"] == 1
    assert review["review_summary"]["matched_target_count"] == 1
    assert review["review_summary"]["review_mode"] == "challenge_review"
    assert review["review_summary"]["review_scope"] == "multi_target"


def test_bundle_types_fill_negative_defaults() -> None:
    runner = _DummyRunner()
    plan = _make_plan()

    context = runner._normalize_context_bundle(plan, {"candidate_count": None})
    planning = runner._normalize_plan_bundle({"goal": "foo"})
    review = runner._normalize_review_bundle({"status": "not_applicable"})

    assert context["trace"] == plan.trace.to_dict()
    assert context["binding_summary"] == "not_applicable"
    assert context["query_units"] == []
    assert planning["planning_mode"] == "not_applicable"
    assert planning["plan_summary"]["step_count"] == 0
    assert planning["plan_summary"]["fallback_used"] is False
    assert review["targets"] == []
    assert review["review_findings"] == []
    assert review["review_summary"]["review_mode"] == "not_applicable"
    assert review["review_summary"]["follow_up_retrieval_attempted"] is False
