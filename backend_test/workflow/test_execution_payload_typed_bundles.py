from __future__ import annotations

from workflow.types import (
    ChallengeResultBundle,
    ChallengeResultBundleSummaryView,
    ContextBundle,
    ContextBindingResult,
    EvidenceBundle,
    EvidenceAssessmentResult,
    EvidenceRefCandidate,
    EvidenceItem,
    ExecutionPayload,
    PlanBundle,
    ReviewEvaluationResult,
    RetrievalUnitResult,
    ReviewBundle,
)


def test_execution_payload_accepts_typed_bundles_and_serializes_contract() -> None:
    payload = ExecutionPayload(
        route="qa",
        handling_mode="challenge",
        action="respond",
        key_events=("binding_applied", "follow_up_retrieval_attempted"),
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
    assert result["challenge_result_bundle"] == result["review_bundle"]
    assert result["review_bundle"]["review_summary"]["unsupported_target_refs"] == ["claim_2"]
    assert result["evidence_bundle"]["evidence_summary"]["retrieval_quality_status"] == "good"
    assert result["key_events"] == ["binding_applied", "follow_up_retrieval_attempted"]


def test_execution_payload_summary_views_consume_typed_bundles() -> None:
    payload = ExecutionPayload(
        route="orchestrated",
        handling_mode="normal",
        action="respond",
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
    assert payload.context_bundle_obj().summary_view() == context_view
    assert payload.plan_bundle_obj().summary_view() == plan_view
    assert payload.review_bundle_obj().summary_view() == review_view


def test_execution_payload_exposes_challenge_result_bundle_alias_views() -> None:
    payload = ExecutionPayload(
        route="qa",
        handling_mode="challenge",
        action="respond",
        review_bundle=ReviewBundle(
            review_mode="challenge_review",
            review_confidence="medium",
            review_scope="single_target",
            status="success",
            targets=({"target_ref": "claim_1"},),
            review_summary={
                "status_summary": "success",
                "matched_target_count": 1,
                "target_count": 1,
            },
        ),
    )

    bundle = payload.challenge_result_bundle_obj()
    summary = payload.challenge_result_summary_view()

    assert isinstance(bundle, ChallengeResultBundle)
    assert isinstance(summary, ChallengeResultBundleSummaryView)
    assert summary.status_summary == "success"
    assert summary.target_count == 1


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
            "target_count": 2,
            "matched_target_count": 1,
            "matched_target_refs": ["claim_1"],
            "unsupported_target_refs": ["claim_2"],
            "needs_more_evidence_targets": ["claim_2"],
            "status_summary": "partial_success",
            "follow_up_retrieval_sources": ["kb/law.md"],
            "follow_up_retrieval_retrieved_evidence_count": 1,
        },
    )

    assert bundle.target_count() == 2
    assert bundle.matched_target_count() == 1
    assert bundle.status_summary() == "partial_success"
    assert bundle.matched_target_refs() == ("claim_1",)
    assert bundle.unsupported_target_refs() == ("claim_2",)
    assert bundle.needs_more_evidence_targets() == ("claim_2",)
    assert bundle.follow_up_retrieval_attempted() is False
    assert bundle.follow_up_retrieval_improved() is False
    assert bundle.follow_up_retrieval_sources() == ("kb/law.md",)
    assert bundle.follow_up_retrieval_retrieved_evidence_count() == 1


def test_review_bundle_can_be_built_from_challenge_result_inputs() -> None:
    bundle = ReviewBundle.from_challenge_result(
        status="partial_success",
        targets=(
            {"object_id": "claim_1"},
            {"object_id": "claim_2"},
        ),
        evidence_assessment={
            "partially_sufficient": True,
            "matched_target_count": 1,
            "needs_more_evidence_targets": ["claim_2"],
            "follow_up_retrieval": {
                "attempted": True,
                "improved": False,
                "source_refs": ["kb/law.md"],
                "retrieved_evidence_count": 1,
            },
        },
        review_findings=(
            {"target_ref": "claim_1", "judgment": "supported"},
            {"target_ref": "claim_2", "judgment": "insufficient_evidence"},
        ),
    )

    assert bundle.review_mode == "challenge_review"
    assert bundle.review_confidence == "medium"
    assert bundle.review_scope == "multi_target"
    assert bundle.matched_target_refs() == ("claim_1",)
    assert bundle.needs_more_evidence_targets() == ("claim_2",)
    assert bundle.follow_up_retrieval_attempted() is True


def test_challenge_result_can_export_challenge_result_bundle_alias() -> None:
    challenge = ReviewEvaluationResult(
        status="partial_success",
        review_findings=(
            {"target_ref": "claim_1", "judgment": "supported"},
            {"target_ref": "claim_2", "judgment": "insufficient_evidence"},
        ),
        answer_constraints={"must_cite_sources": True},
    )
    result = ExecutionPayload(
        route="qa",
        handling_mode="challenge",
        action="respond",
    )
    # 保留一个极小黑盒：alias path 应稳定返回兼容 bundle/view。
    bundle = ReviewBundle.from_review_evaluation(
        targets=(
            {"object_id": "claim_1"},
            {"object_id": "claim_2"},
        ),
        evidence_assessment=EvidenceAssessmentResult(
            partially_sufficient=True,
            matched_target_count=1,
            target_count=2,
            needs_more_evidence_targets=("claim_2",),
        ),
        evaluation=challenge,
    )

    payload = ExecutionPayload(
        route=result.route,
        handling_mode=result.handling_mode,
        action=result.action,
        review_bundle=bundle,
    )

    assert payload.challenge_result_bundle_obj().review_mode == "challenge_review"
    assert payload.challenge_result_summary_view().needs_more_evidence_target_count == 1


def test_review_bundle_can_be_built_directly_from_review_evaluation() -> None:
    bundle = ReviewBundle.from_review_evaluation(
        targets=(
            {"object_id": "claim_1"},
            {"object_id": "claim_2"},
        ),
        evidence_assessment=EvidenceAssessmentResult(
            partially_sufficient=True,
            matched_target_count=1,
            target_count=2,
            needs_more_evidence_targets=("claim_2",),
        ),
        evaluation=ReviewEvaluationResult(
            status="partial_success",
            review_findings=(
                {"target_ref": "claim_1", "judgment": "supported"},
                {"target_ref": "claim_2", "judgment": "insufficient_evidence"},
            ),
            answer_constraints={"must_cite_sources": True},
        ),
    )

    assert bundle.review_mode == "challenge_review"
    assert bundle.review_confidence == "medium"
    assert bundle.matched_target_refs() == ("claim_1",)
    assert bundle.needs_more_evidence_targets() == ("claim_2",)


def test_review_bundle_summary_view_prefers_assessment_owner_counts_and_follow_up_flags() -> None:
    bundle = ReviewBundle(
        review_mode="challenge_review",
        review_confidence="medium",
        review_scope="multi_target",
        status="partial_success",
        targets=(),
        evidence_assessment=EvidenceAssessmentResult(
            partially_sufficient=True,
            matched_target_count=1,
            target_count=2,
            needs_more_evidence_targets=("claim_2",),
            follow_up_retrieval={
                "attempted": True,
                "improved": False,
            },
        ),
        review_summary={
            "target_count": 0,
            "matched_target_count": 0,
            "needs_more_evidence_targets": [],
            "follow_up_retrieval_attempted": False,
            "follow_up_retrieval_improved": True,
        },
    )

    summary_view = bundle.summary_view()

    assert summary_view.target_count == 2
    assert summary_view.matched_target_count == 1
    assert summary_view.needs_more_evidence_target_count == 1
    assert summary_view.follow_up_retrieval_attempted is True
    assert summary_view.follow_up_retrieval_improved is False


def test_review_bundle_accessors_prefer_assessment_owner_over_summary_fallback() -> None:
    bundle = ReviewBundle(
        review_mode="challenge_review",
        review_confidence="medium",
        review_scope="multi_target",
        status="partial_success",
        targets=(),
        evidence_assessment=EvidenceAssessmentResult(
            partially_sufficient=True,
            matched_target_count=1,
            target_count=2,
            matched_target_refs=("claim_1",),
            unsupported_target_refs=("claim_2",),
            needs_more_evidence_targets=("claim_2",),
            follow_up_retrieval={
                "attempted": True,
                "improved": False,
                "source_refs": ["kb/law.md"],
                "retrieved_evidence_count": 1,
            },
        ),
        review_summary={
            "target_count": 0,
            "matched_target_count": 0,
            "matched_target_refs": [],
            "unsupported_target_refs": [],
            "needs_more_evidence_targets": [],
            "follow_up_retrieval_attempted": False,
            "follow_up_retrieval_improved": True,
            "follow_up_retrieval_sources": [],
            "follow_up_retrieval_retrieved_evidence_count": 0,
        },
    )

    assert bundle.target_count() == 2
    assert bundle.matched_target_count() == 1
    assert bundle.matched_target_refs() == ("claim_1",)
    assert bundle.unsupported_target_refs() == ("claim_2",)
    assert bundle.needs_more_evidence_targets() == ("claim_2",)
    assert bundle.follow_up_retrieval_attempted() is True
    assert bundle.follow_up_retrieval_improved() is False
    assert bundle.follow_up_retrieval_sources() == ("kb/law.md",)
    assert bundle.follow_up_retrieval_retrieved_evidence_count() == 1


def test_review_bundle_summary_obj_and_to_dict_prefer_assessment_owner_over_summary_fallback() -> None:
    bundle = ReviewBundle(
        review_mode="challenge_review",
        review_confidence="medium",
        review_scope="multi_target",
        status="partial_success",
        evidence_assessment=EvidenceAssessmentResult(
            partially_sufficient=True,
            matched_target_count=1,
            target_count=2,
            matched_target_refs=("claim_1",),
            unsupported_target_refs=("claim_2",),
            needs_more_evidence_targets=("claim_2",),
            follow_up_retrieval={
                "attempted": False,
                "improved": False,
                "source_refs": ["kb/law.md"],
                "retrieved_evidence_count": 1,
            },
        ),
        review_summary={
            "target_count": 99,
            "matched_target_count": 88,
            "matched_target_refs": ["stale_claim"],
            "unsupported_target_refs": ["stale_unsupported"],
            "needs_more_evidence_targets": ["stale_missing"],
            "follow_up_retrieval_attempted": True,
            "follow_up_retrieval_improved": True,
            "follow_up_retrieval_sources": ["stale.md"],
            "follow_up_retrieval_retrieved_evidence_count": 42,
        },
    )

    summary = bundle.summary_obj()
    exported = bundle.to_dict()["review_summary"]

    assert summary["target_count"] == 2
    assert summary["matched_target_count"] == 1
    assert summary["matched_target_refs"] == ["claim_1"]
    assert summary["unsupported_target_refs"] == ["claim_2"]
    assert summary["needs_more_evidence_targets"] == ["claim_2"]
    assert summary["follow_up_retrieval_attempted"] is False
    assert summary["follow_up_retrieval_improved"] is False
    assert summary["follow_up_retrieval_sources"] == ["kb/law.md"]
    assert summary["follow_up_retrieval_retrieved_evidence_count"] == 1
    assert exported == summary


def test_review_bundle_preserves_explicit_zero_counts_from_assessment_owner() -> None:
    bundle = ReviewBundle(
        review_mode="challenge_review",
        review_confidence="low",
        review_scope="single_target",
        status="insufficient_evidence",
        evidence_assessment=EvidenceAssessmentResult(
            partially_sufficient=True,
            target_count=0,
            matched_target_count=0,
            retrieve_if_needed={"needed": False},
        ),
        review_summary={
            "target_count": 99,
            "matched_target_count": 88,
            "needs_more_evidence_targets": ["stale_missing"],
        },
    )

    summary_view = bundle.summary_view()
    summary_obj = bundle.summary_obj()

    assert summary_view.target_count == 0
    assert summary_view.matched_target_count == 0
    assert summary_view.needs_more_evidence_target_count == 0
    assert bundle.target_count() == 0
    assert bundle.matched_target_count() == 0
    assert summary_obj["target_count"] == 0
    assert summary_obj["matched_target_count"] == 0


def test_evidence_bundle_accessors_expose_summary_state() -> None:
    bundle = EvidenceBundle(
        query_unit_results=(
            RetrievalUnitResult(unit_id="q1", query="foo", origin="primary"),
            {"unit_id": "q2", "query": "bar", "origin": "support"},
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
        source_refs=("kb/law.md", "kb/guide.md"),
        coverage_summary={"query_units": 2, "sources": 2},
        quality_summary={"average_weighted_score": 0.4, "status": "bad", "repaired_units": 1},
        missing_evidence_notes=("retrieval_quality_weak",),
    )

    assert bundle.summary_obj()["retrieval_quality_status"] == "bad"
    assert bundle.query_unit_count() == 2
    assert bundle.merged_evidence_count() == 1
    assert bundle.source_ref_count() == 2
    assert bundle.source_ref_list() == ["kb/law.md", "kb/guide.md"]
    assert isinstance(bundle.query_unit_result_objs()[0], RetrievalUnitResult)
    assert bundle.retrieval_quality_status() == "bad"
    assert bundle.repairable_unit_count() == 0
    assert bundle.repaired_unit_count() == 1
    assert bundle.missing_evidence_flag() is True
    assert bundle.coverage_query_unit_count() == 2
    assert bundle.coverage_source_count() == 2
    candidates = bundle.to_evidence_ref_candidates()
    assert candidates[0]["object_id"] == "e1"
    assert candidates[0]["object_type"] == "evidence_ref"
    assert candidates[0]["refs"] == ["e1", "kb/law.md", "section-19"]
    candidate_objs = bundle.to_evidence_ref_candidate_objs()
    assert isinstance(candidate_objs[0], EvidenceRefCandidate)
    assert candidate_objs[0].all_refs() == ("e1", "e1", "kb/law.md", "section-19")
    summary_view = bundle.summary_view()
    assert summary_view.retrieval_quality_status == "bad"
    assert summary_view.query_unit_count == 2
    assert summary_view.source_ref_count == 2
    assert summary_view.repairable_units == 0
    assert summary_view.repaired_units == 1
    assert summary_view.missing_evidence is True
    assert summary_view.coverage_query_units == 2
    assert summary_view.coverage_sources == 2
    assert bundle.summary_obj()["coverage_query_units"] == 2
    assert bundle.summary_obj()["repairable_units"] == 0


def test_query_unit_accessors_remain_consistent_across_bundles() -> None:
    query_units = (
        {"unit_id": "q1", "text": "A是什么"},
        {"unit_id": "q2", "text": "B风险"},
    )
    context_bundle = ContextBundle(query_units=query_units)
    plan_bundle = PlanBundle(
        planning_mode="compare",
        query_units=query_units,
        ordered_steps=({"title": "Compare", "sequence": 1}, {"title": "Explain", "sequence": 2}),
        comparison_units=({"left": "A", "right": "B"},),
        execution_checkpoints=({"name": "coverage"},),
        bound_target_refs=("compare_1",),
        refined=True,
        fallback_used=False,
    )

    assert context_bundle.query_unit_dicts() == query_units
    assert plan_bundle.query_unit_dicts() == query_units
    assert plan_bundle.summary_obj()["planning_mode"] == "compare"
    assert plan_bundle.step_count() == 2
    assert plan_bundle.checkpoint_count() == 1
    assert plan_bundle.comparison_unit_count() == 1
    assert plan_bundle.bound_target_ref_count() == 1
    assert plan_bundle.is_refined() is True
    assert plan_bundle.is_fallback() is False
    assert context_bundle.summary_view().query_unit_count == 2
    assert plan_bundle.summary_view().step_count == 2


def test_plan_bundle_summary_exports_remain_consistent() -> None:
    plan_bundle = PlanBundle(
        planning_mode="compare",
        ordered_steps=({"title": "Compare", "sequence": 1}, {"title": "Explain", "sequence": 2}),
        comparison_units=({"left": "A", "right": "B"},),
        execution_checkpoints=({"name": "coverage"},),
        bound_target_refs=("compare_1",),
        refined=True,
        fallback_used=True,
        fallback_reason=("fallback_for_missing_context",),
    )

    summary_dict = plan_bundle.summary_dict()
    summary_obj = plan_bundle.summary_obj()
    exported_summary = plan_bundle.to_dict()["plan_summary"]

    assert summary_dict["planning_mode"] == "compare"
    assert summary_dict["step_count"] == 2
    assert summary_dict["checkpoint_count"] == 1
    assert summary_dict["comparison_unit_count"] == 1
    assert summary_dict["bound_target_ref_count"] == 1
    assert summary_dict["refined"] is True
    assert summary_dict["fallback_used"] is True
    assert summary_dict["fallback_reason"] == ["fallback_for_missing_context"]
    assert summary_obj == summary_dict
    assert exported_summary == summary_dict
