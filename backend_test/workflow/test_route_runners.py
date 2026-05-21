from __future__ import annotations

from intent.schema.intent_types import ControlTrace, IntentModifiers
from workflow.runners.base import RouteExecutionRequest
from workflow.runners.orchestrated_runner import OrchestratedRouteRunner
from workflow.runners.qa_runner import QaRouteRunner
from workflow.types import EvidenceBundle, EvidenceItem, WorkflowPlan, WorkflowPolicyFlags


class _FakeRetrievalPower:
    def retrieve(self, query_units, *, top_k: int = 4) -> EvidenceBundle:
        del top_k
        return EvidenceBundle(
            query_unit_results=tuple(
                {
                    "unit_id": unit.unit_id,
                    "query": unit.text,
                    "origin": unit.origin,
                }
                for unit in query_units
            ),
            merged_evidence_items=(
                EvidenceItem(
                    evidence_id="evidence_2",
                    source_path="kb/law.md",
                    source_type="official_structured",
                    locator="section-19",
                    snippet="一年期合同试用期上限一个月。",
                    channel="vector",
                    score=0.92,
                    query_unit_ids=tuple(unit.unit_id for unit in query_units),
                ),
            ),
            source_refs=("kb/law.md",),
            coverage_summary={"query_units": len(query_units), "sources": 1},
            quality_summary={"average_weighted_score": 0.9},
            missing_evidence_notes=(),
        )


def _make_plan(
    *,
    route: str,
    handling_mode: str,
    enabled_powers: tuple[str, ...] = (),
    use_planner: bool = False,
    decompose_query: bool = False,
    use_context: bool = False,
) -> WorkflowPlan:
    trace = ControlTrace(
        main_intent="qa",
        modifiers=IntentModifiers(challenge=handling_mode == "challenge"),
        task_complexity="complex" if use_planner else "simple",
        task_shape="compare" if use_planner else "single_question",
        task_topology="parallel_queries" if decompose_query else "single",
        context_dependency="previous_answer" if use_context else "none",
        ambiguity_states=("history_dependent",) if use_context else (),
        missing_context_types=(),
        decision_strength="high",
        decision_source="rule",
        decision_reason="test",
    )
    return WorkflowPlan(
        route=route,
        handling_mode=handling_mode,
        action="agent",
        use_context=use_context,
        cite_sources=True,
        use_planner=use_planner,
        decompose_query=decompose_query,
        rewrite_query=use_context,
        should_ask_clarification_first=False,
        trace=trace,
        enabled_powers=enabled_powers,  # type: ignore[arg-type]
        knowledge_scope_status="resolved",
        policy_flags=WorkflowPolicyFlags(
            need_planner=use_planner,
            need_query_decomposition=decompose_query,
            need_context_binding=use_context,
        ),
        notes=("test",),
    )


def test_orchestrated_runner_builds_plan_and_binding_bundle() -> None:
    runner = OrchestratedRouteRunner()
    plan = _make_plan(
        route="orchestrated",
        handling_mode="normal",
        enabled_powers=("context_binding_power", "planning_power", "decomposition_power"),
        use_planner=True,
        decompose_query=True,
        use_context=True,
    )
    request = RouteExecutionRequest(
        message="比较A和B？再分别说明两者风险？",
        messages=[{"role": "user", "content": "比较A和B？再分别说明两者风险？"}],
        context={
            "registry_entries": [
                {
                    "object_id": "compare_1",
                    "object_type": "comparison_target",
                    "content": "A vs B",
                    "source_power": "planning_power",
                    "refs": ["compare_1"],
                }
            ],
            "recent_power": "planning_power",
            "recent_object_type": "comparison_target",
        },
    )

    payload = runner.run(plan, request)

    assert "binding" in payload.context_bundle
    assert payload.context_bundle["binding"]["binding_ambiguous"] is False
    assert payload.context_bundle["binding_summary"]
    assert "query_units" in payload.context_bundle
    assert payload.plan_bundle["ordered_steps"]
    assert payload.plan_bundle["goal"] == request.message
    assert payload.plan_bundle["task_shape"] == "compare"
    assert payload.plan_bundle["task_topology"] == "parallel_queries"
    assert payload.plan_bundle["planning_mode"] == "compare"
    assert payload.plan_bundle["query_units"][0]["unit_id"] == "q1"
    assert payload.plan_bundle["execution_checkpoints"]
    assert payload.plan_bundle["bound_target_refs"]
    assert payload.plan_bundle["fallback_used"] is False
    assert payload.plan_bundle["refined"] is False
    assert payload.plan_bundle["plan_summary"]["planning_mode"] == "compare"
    assert payload.plan_bundle["plan_summary"]["fallback_used"] is False
    assert payload.review_bundle["status"] == "not_applicable"
    assert payload.review_bundle["review_summary"]["status_summary"] == "not_applicable"
    assert payload.review_bundle["review_mode"] == "not_applicable"
    assert payload.review_bundle["review_confidence"] == "not_applicable"
    assert payload.review_bundle["review_scope"] == "not_applicable"
    assert payload.review_bundle["review_summary"]["review_mode"] == "not_applicable"
    assert payload.review_bundle["review_summary"]["review_confidence"] == "not_applicable"
    assert payload.review_bundle["review_summary"]["review_scope"] == "not_applicable"
    assert payload.review_bundle["review_summary"]["follow_up_retrieval_attempted"] is False
    assert payload.context_bundle["candidate_count"] == 1
    assert payload.context_bundle["query_units"]


def test_qa_runner_challenge_without_candidates_requests_clarification() -> None:
    runner = QaRouteRunner()
    plan = _make_plan(
        route="qa",
        handling_mode="challenge",
        enabled_powers=("challenge_power",),
    )
    request = RouteExecutionRequest(
        message="你刚才说的依据是什么？",
        messages=[{"role": "user", "content": "你刚才说的依据是什么？"}],
        context={"registry_entries": []},
    )

    payload = runner.run(plan, request)

    assert payload.status == "needs_clarification"
    assert payload.review_bundle["status"] == "needs_clarification"
    assert payload.review_bundle["review_summary"]["target_count"] == 0
    assert payload.review_bundle["review_summary"]["status_summary"] == "needs_clarification"
    assert payload.review_bundle["review_mode"] == "challenge_review"
    assert payload.review_bundle["review_confidence"] == "low"
    assert payload.review_bundle["review_scope"] == "not_applicable"
    assert payload.review_bundle["review_summary"]["follow_up_retrieval_attempted"] is False
    assert payload.review_bundle["targets"] == []
    assert payload.review_bundle["review_findings"] == []


def test_qa_runner_challenge_with_evidence_candidates_returns_review_bundle() -> None:
    runner = QaRouteRunner()
    plan = _make_plan(
        route="qa",
        handling_mode="challenge",
        enabled_powers=("challenge_power", "context_binding_power"),
        use_context=True,
    )
    request = RouteExecutionRequest(
        message="你刚才这个依据是什么？",
        messages=[{"role": "user", "content": "你刚才这个依据是什么？"}],
        context={
            "registry_entries": [
                {
                    "object_id": "claim_1",
                    "object_type": "claim",
                    "content": "试用期最长一个月",
                    "source_power": "challenge_power",
                    "refs": ["evidence_1"],
                },
                {
                    "object_id": "evidence_1",
                    "object_type": "evidence_ref",
                    "content": "劳动合同法第19条",
                    "source_power": "retrieval_power",
                    "refs": ["evidence_1"],
                },
            ],
            "recent_power": "challenge_power",
            "recent_object_type": "claim",
        },
    )

    payload = runner.run(plan, request)

    assert payload.status == "ready"
    assert payload.review_bundle["status"] == "success"
    assert payload.review_bundle["evidence_assessment"]["sufficient"] is True
    assert payload.review_bundle["evidence_assessment"]["retrieve_if_needed"]["needed"] is False
    assert payload.context_bundle["binding"] is not None
    assert payload.context_bundle["binding_summary"]
    assert payload.review_bundle["review_mode"] == "challenge_review"
    assert payload.review_bundle["review_confidence"] == "high"
    assert payload.review_bundle["review_scope"] == "single_target"
    assert isinstance(payload.review_bundle["targets"], list)
    assert isinstance(payload.review_bundle["review_findings"], list)
    assert payload.review_bundle["review_summary"]["matched_target_refs"] == ["claim_1"]
    assert payload.review_bundle["review_summary"]["status_summary"] == "success"


def test_qa_runner_challenge_supports_multi_target_partial_review_bundle() -> None:
    runner = QaRouteRunner()
    plan = _make_plan(
        route="qa",
        handling_mode="challenge",
        enabled_powers=("challenge_power",),
    )
    request = RouteExecutionRequest(
        message="前两个结论的依据都对吗？",
        messages=[{"role": "user", "content": "前两个结论的依据都对吗？"}],
        context={
            "registry_entries": [
                {
                    "object_id": "claim_1",
                    "object_type": "claim",
                    "content": "试用期最长一个月",
                    "source_power": "challenge_power",
                    "refs": ["evidence_1"],
                },
                {
                    "object_id": "claim_2",
                    "object_type": "claim",
                    "content": "一年期合同试用期上限一个月",
                    "source_power": "challenge_power",
                    "refs": ["evidence_2"],
                },
                {
                    "object_id": "evidence_1",
                    "object_type": "evidence_ref",
                    "content": "劳动合同法第19条",
                    "source_power": "retrieval_power",
                    "refs": ["evidence_1"],
                },
            ],
        },
    )

    payload = runner.run(plan, request)

    assert payload.status == "ready"
    assert payload.review_bundle["status"] == "partial_success"
    assert payload.review_bundle["evidence_assessment"]["partially_sufficient"] is True
    assert payload.review_bundle["evidence_assessment"]["needs_more_evidence_targets"] == ["claim_2"]
    assert len(payload.review_bundle["review_findings"]) == 2
    assert payload.review_bundle["review_mode"] == "challenge_review"
    assert payload.review_bundle["review_confidence"] == "medium"
    assert payload.review_bundle["review_scope"] == "multi_target"
    assert len(payload.review_bundle["targets"]) == 2
    assert payload.review_bundle["review_summary"]["unsupported_target_refs"] == ["claim_2"]
    assert payload.review_bundle["review_summary"]["needs_more_evidence_targets"] == ["claim_2"]
    assert payload.review_bundle["review_summary"]["status_summary"] == "partial_success"
    assert payload.review_bundle["review_summary"]["follow_up_retrieval_attempted"] is False


def test_qa_runner_challenge_can_resolve_missing_targets_via_follow_up_retrieval() -> None:
    runner = QaRouteRunner()
    runner.retrieval_power = _FakeRetrievalPower()
    plan = _make_plan(
        route="qa",
        handling_mode="challenge",
        enabled_powers=("challenge_power", "retrieval_power"),
    )
    request = RouteExecutionRequest(
        message="前两个结论的依据都对吗？",
        messages=[{"role": "user", "content": "前两个结论的依据都对吗？"}],
        context={
            "registry_entries": [
                {
                    "object_id": "claim_1",
                    "object_type": "claim",
                    "content": "试用期最长一个月",
                    "source_power": "challenge_power",
                    "refs": ["evidence_1"],
                },
                {
                    "object_id": "claim_2",
                    "object_type": "claim",
                    "content": "一年期合同试用期上限一个月",
                    "source_power": "challenge_power",
                    "refs": ["evidence_2"],
                },
                {
                    "object_id": "evidence_1",
                    "object_type": "evidence_ref",
                    "content": "劳动合同法第19条",
                    "source_power": "retrieval_power",
                    "refs": ["evidence_1"],
                },
            ],
        },
    )

    payload = runner.run(plan, request)

    assert payload.status == "ready"
    assert payload.review_bundle["status"] == "success"
    assert payload.review_bundle["evidence_assessment"]["follow_up_retrieval"]["attempted"] is True
    assert payload.review_bundle["review_mode"] == "challenge_review"
    assert payload.review_bundle["review_confidence"] == "medium"
    assert payload.review_bundle["review_scope"] == "multi_target"
    assert len(payload.review_bundle["targets"]) == 2
    assert payload.review_bundle["review_summary"]["matched_target_count"] == 2
    assert payload.review_bundle["review_summary"]["unsupported_target_refs"] == []
    assert payload.review_bundle["review_summary"]["follow_up_retrieval_attempted"] is True
    assert payload.review_bundle["review_summary"]["follow_up_retrieval_sources"] == ["kb/law.md"]


def test_orchestrated_runner_uses_staged_planning_mode_for_staged_tasks() -> None:
    runner = OrchestratedRouteRunner()
    trace = ControlTrace(
        main_intent="qa",
        modifiers=IntentModifiers(),
        task_complexity="complex",
        task_shape="verify",
        task_topology="staged",
        context_dependency="none",
        ambiguity_states=(),
        missing_context_types=(),
        decision_strength="high",
        decision_source="rule",
        decision_reason="test",
    )
    plan = WorkflowPlan(
        route="orchestrated",
        handling_mode="normal",
        action="agent",
        use_context=False,
        cite_sources=True,
        use_planner=True,
        decompose_query=False,
        rewrite_query=False,
        should_ask_clarification_first=False,
        trace=trace,
        enabled_powers=("planning_power",),
        knowledge_scope_status="resolved",
        policy_flags=WorkflowPolicyFlags(need_planner=True),
        notes=("test",),
    )
    request = RouteExecutionRequest(
        message="先核验法规前提，再给出最终结论。",
        messages=[{"role": "user", "content": "先核验法规前提，再给出最终结论。"}],
        context={},
    )

    payload = runner.run(plan, request)

    assert payload.plan_bundle["planning_mode"] == "staged"
    assert payload.plan_bundle["fallback_used"] is False
    assert payload.plan_bundle["plan_summary"]["planning_mode"] == "staged"
    titles = [step["title"] for step in payload.plan_bundle["ordered_steps"]]
    assert "Preserve stage dependencies" in titles
