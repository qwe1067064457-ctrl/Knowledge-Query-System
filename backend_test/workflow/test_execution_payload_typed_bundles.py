from __future__ import annotations

from workflow.types import (
    ContextBundle,
    ContextBindingResult,
    EvidenceBundle,
    EvidenceItem,
    ExecutionPayload,
    PlanBundle,
    ReviewBundle,
)


def test_execution_payload_accepts_typed_bundles_and_serializes_contract() -> None:
    payload = ExecutionPayload(
        route="qa",
        handling_mode="challenge",
        action="respond",
        context_bundle=ContextBundle(
            trace={"main_intent": "qa"},
            binding={"bound_targets": [{"ref": "claim_1"}]},
            binding_summary="pattern_match",
            candidate_count=2,
            query_units=({"unit_id": "q1", "text": "foo"},),
        ),
        evidence_bundle=EvidenceBundle(
            query_unit_results=(
                {"unit_id": "q1", "query": "foo", "origin": "primary"},
            ),
            merged_evidence_items=(
                EvidenceItem(
                    evidence_id="e1",
                    source_path="kb/law.md",
                    source_type="official_structured",
                    locator="section-19",
                    snippet="一年期合同试用期上限一个月。",
                    channel="vector",
                    score=0.9,
                    query_unit_ids=("q1",),
                ),
            ),
            source_refs=("kb/law.md",),
            coverage_summary={"query_units": 1, "sources": 1},
            quality_summary={"average_weighted_score": 0.9},
            missing_evidence_notes=(),
        ),
        plan_bundle=PlanBundle(
            goal="比较A和B",
            task_shape="compare",
            task_topology="parallel_queries",
            planning_mode="compare",
            query_units=({"unit_id": "q1", "text": "比较A和B"},),
            ordered_steps=({"title": "Compare", "sequence": 1},),
            comparison_units=({"left": "A", "right": "B"},),
            execution_checkpoints=({"name": "coverage"},),
            bound_target_refs=("compare_1",),
            refined=True,
            fallback_used=False,
            fallback_reason=(),
        ),
        review_bundle=ReviewBundle(
            review_mode="challenge_review",
            review_confidence="medium",
            review_scope="multi_target",
            status="partial_success",
            targets=({"target_ref": "claim_1"}, {"target_ref": "claim_2"}),
            evidence_assessment={"partially_sufficient": True},
            review_findings=({"target_ref": "claim_1", "judgment": "supported"},),
            review_summary={
                "matched_target_count": 1,
                "matched_target_refs": ["claim_1"],
                "unsupported_target_refs": ["claim_2"],
                "needs_more_evidence_targets": ["claim_2"],
            },
        ),
    )

    result = payload.to_dict()

    assert result["context_bundle"]["binding_summary"] == "pattern_match"
    assert result["context_bundle"]["query_units"][0]["unit_id"] == "q1"
    assert result["plan_bundle"]["plan_summary"]["planning_mode"] == "compare"
    assert result["plan_bundle"]["query_units"][0]["unit_id"] == "q1"
    assert result["review_bundle"]["review_mode"] == "challenge_review"
    assert result["review_bundle"]["review_summary"]["unsupported_target_refs"] == ["claim_2"]
    assert result["evidence_bundle"]["evidence_summary"]["retrieval_quality_status"] == "good"


def test_execution_payload_summary_views_consume_typed_bundles() -> None:
    payload = ExecutionPayload(
        route="orchestrated",
        handling_mode="normal",
        action="agent",
        context_bundle=ContextBundle(
            trace={"main_intent": "qa"},
            binding=None,
            binding_summary="topic_continuity",
            candidate_count=3,
            query_units=(
                {"unit_id": "q1", "text": "A是什么"},
                {"unit_id": "q2", "text": "B风险"},
            ),
        ),
        plan_bundle=PlanBundle(
            planning_mode="staged",
            ordered_steps=(
                {"title": "Step1", "sequence": 1},
                {"title": "Step2", "sequence": 2},
            ),
            execution_checkpoints=({"name": "coverage"},),
            fallback_used=True,
            fallback_reason=("planner_validation_failed",),
        ),
        review_bundle=ReviewBundle(
            review_mode="challenge_review",
            review_confidence="low",
            review_scope="single_target",
            status="insufficient_evidence",
            targets=({"target_ref": "claim_1"},),
            review_summary={
                "status_summary": "insufficient_evidence",
                "needs_more_evidence_targets": ["claim_1"],
                "follow_up_retrieval_attempted": True,
                "follow_up_retrieval_improved": False,
            },
        ),
    )

    context_view = payload.context_summary_view()
    plan_view = payload.plan_summary_view()
    review_view = payload.review_summary_view()

    assert context_view.binding_summary == "topic_continuity"
    assert context_view.candidate_count == 3
    assert context_view.query_unit_count == 2
    assert plan_view.planning_mode == "staged"
    assert plan_view.step_count == 2
    assert plan_view.fallback_used is True
    assert review_view.review_mode == "challenge_review"
    assert review_view.review_confidence == "low"
    assert review_view.review_scope == "single_target"
    assert review_view.needs_more_evidence_target_count == 1
    assert review_view.follow_up_retrieval_attempted is True


def test_context_bundle_accepts_typed_binding_result() -> None:
    bundle = ContextBundle(
        trace={"main_intent": "qa"},
        binding=ContextBindingResult(
            bound_targets=({"object_id": "claim_1", "content": "最新结论"},),
            binding_confidence="high",
            binding_ambiguous=False,
            matched_by="explicit_pattern",
            binding_summary="Bound via explicit pattern.",
        ),
        binding_summary="Bound via explicit pattern.",
        candidate_count=1,
        query_units=({"unit_id": "q1", "text": "foo"},),
    )

    payload = bundle.to_dict()

    assert payload["binding"]["bound_targets"][0]["object_id"] == "claim_1"
    assert payload["binding"]["matched_by"] == "explicit_pattern"
    assert payload["query_units"][0]["unit_id"] == "q1"
    assert bundle.bound_targets()[0]["object_id"] == "claim_1"


def test_review_bundle_accessors_expose_summary_targets() -> None:
    bundle = ReviewBundle(
        review_mode="challenge_review",
        review_confidence="medium",
        review_scope="multi_target",
        status="partial_success",
        targets=({"target_ref": "claim_1"}, {"target_ref": "claim_2"}),
        review_summary={
            "matched_target_refs": ["claim_1"],
            "unsupported_target_refs": ["claim_2"],
            "needs_more_evidence_targets": ["claim_2"],
        },
    )

    assert bundle.matched_target_refs() == ("claim_1",)
    assert bundle.unsupported_target_refs() == ("claim_2",)
    assert bundle.needs_more_evidence_targets() == ("claim_2",)
