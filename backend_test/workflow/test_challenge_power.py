from __future__ import annotations

from workflow.powers.challenge_power import ChallengePower
from workflow.orchestrated.execution_layer.adapters.retrieval_adapter import build_retrieval_workers
from workflow.orchestrated.execution_layer.adapters.review_adapter import build_review_workers
from workflow.orchestrated.execution_layer.workers.registry import WorkerRegistry
from workflow.types import (
    ChallengeResult,
    EvidenceAssessmentResult,
    EvidenceBundle,
    EvidenceItem,
    EvidenceRefCandidate,
    ReviewEvaluationResult,
)
from workflow.workers.binding_worker import BindingWorker
from workflow.workers.review_worker import ReviewWorker


class _FakeRetrievalPower:
    def __init__(self) -> None:
        self.last_queries = []

    def retrieve(self, query_units, *, top_k: int = 4, path_filters=()) -> EvidenceBundle:
        del top_k
        del path_filters
        assert query_units
        self.last_queries = [unit.text for unit in query_units]
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


def _build_registry(*, review_worker, retrieval_power) -> WorkerRegistry:
    registry = WorkerRegistry()
    for worker in build_retrieval_workers(retrieval_power=retrieval_power, review_worker=review_worker):
        registry.register(worker)
    for worker in build_review_workers(review_worker=review_worker):
        registry.register(worker)
    return registry


def test_challenge_power_returns_success_when_targets_have_matching_evidence() -> None:
    power = ChallengePower()

    result = power.execute(
        query="你刚才这个依据是什么？",
        candidate_targets=[
            {
                "object_id": "claim_1",
                "object_type": "claim",
                "content": "试用期最长一个月",
                "refs": ["evidence_1"],
            }
        ],
        evidence_candidates=[
            {
                "object_id": "evidence_1",
                "object_type": "evidence_ref",
                "content": "劳动合同法第19条",
                "refs": ["evidence_1"],
            }
        ],
        binding_worker=BindingWorker(),
        review_worker=ReviewWorker(),
    )

    assert result.status == "success"
    assert result.evidence_assessment["sufficient"] is True
    assert result.evidence_assessment["retrieve_if_needed"]["needed"] is False
    assert result.review_findings[0]["judgment"] == "supported"
    payload = result.to_dict()
    assert payload["review_summary"]["target_count"] == 1
    assert payload["review_summary"]["matched_target_refs"] == ["claim_1"]
    assert payload["review_summary"]["needs_more_evidence_targets"] == []
    assert payload["review_summary"]["status_summary"] == "success"
    assert payload["review_summary"]["review_mode"] == "challenge_review"
    assert payload["review_summary"]["review_confidence"] == "high"
    assert payload["review_summary"]["review_scope"] == "single_target"
    assert payload["review_summary"]["follow_up_retrieval_attempted"] is False
    assert result.evidence_assessment["target_coverage"] == 1.0
    assert result.evidence_assessment["source_count"] == 1
    assert payload["review_summary"]["follow_up_retrieval_improved"] is False


def test_challenge_power_returns_insufficient_evidence_without_matching_support() -> None:
    power = ChallengePower()

    result = power.execute(
        query="你刚才这个依据是什么？",
        candidate_targets=[
            {
                "object_id": "claim_1",
                "object_type": "claim",
                "content": "试用期最长一个月",
                "refs": ["evidence_1"],
            }
        ],
        evidence_candidates=[],
        binding_worker=BindingWorker(),
        review_worker=ReviewWorker(),
    )

    assert result.status == "insufficient_evidence"
    assert result.evidence_assessment["fallback"] == "evidence_fallback"
    assert result.evidence_assessment["retrieve_if_needed"]["needed"] is True
    assert result.evidence_assessment["needs_more_evidence_targets"] == ["claim_1"]
    assert result.review_findings[0]["judgment"] == "insufficient_evidence"
    assert "fallback_message" in result.answer_constraints
    payload = result.to_dict()
    assert payload["review_summary"]["unsupported_target_refs"] == ["claim_1"]
    assert payload["review_summary"]["status_summary"] == "insufficient_evidence"
    assert payload["review_summary"]["review_mode"] == "challenge_review"
    assert payload["review_summary"]["review_confidence"] == "low"
    assert payload["review_summary"]["review_scope"] == "single_target"
    assert payload["review_summary"]["follow_up_retrieval_attempted"] is False


def test_challenge_power_returns_clarification_question_when_targets_missing() -> None:
    power = ChallengePower()

    result = power.execute(
        query="你刚才说的依据是什么？",
        candidate_targets=[],
        evidence_candidates=[],
        binding_worker=BindingWorker(),
        review_worker=ReviewWorker(),
    )

    assert result.status == "needs_clarification"
    assert "clarification_question" in result.answer_constraints
    payload = result.to_dict()
    assert payload["review_summary"]["target_count"] == 0
    assert payload["review_summary"]["status_summary"] == "needs_clarification"
    assert payload["review_summary"]["review_mode"] == "challenge_review"
    assert payload["review_summary"]["review_confidence"] == "low"
    assert payload["review_summary"]["review_scope"] == "not_applicable"
    assert payload["review_summary"]["follow_up_retrieval_attempted"] is False


def test_challenge_power_requires_explicit_targets_when_only_typed_evidence_candidates_exist() -> None:
    power = ChallengePower()

    result = power.execute(
        query="你刚才引用的法条依据是什么？",
        candidate_targets=[],
        evidence_candidates=[
            EvidenceRefCandidate(
                object_id="evidence_1",
                content="劳动合同法第19条",
                refs=("evidence_1", "section-19"),
                source_type="official_structured",
                channel="vector",
            )
        ],
        binding_worker=BindingWorker(),
        review_worker=ReviewWorker(),
    )

    assert result.status == "needs_clarification"
    assert result.evidence_assessment_obj().sufficient is False
    assert result.review_findings == ()
    payload = result.to_dict()
    assert payload["review_summary"]["matched_target_refs"] == []
    assert payload["review_summary"]["status_summary"] == "needs_clarification"


def test_challenge_power_supports_multi_target_partial_success() -> None:
    power = ChallengePower()

    result = power.execute(
        query="前两个结论的依据都对吗？",
        candidate_targets=[
            {
                "object_id": "claim_1",
                "object_type": "claim",
                "content": "试用期最长一个月",
                "refs": ["evidence_1"],
            },
            {
                "object_id": "claim_2",
                "object_type": "claim",
                "content": "一年期合同试用期上限一个月",
                "refs": ["evidence_2"],
            },
        ],
        evidence_candidates=[
            {
                "object_id": "evidence_1",
                "object_type": "evidence_ref",
                "content": "劳动合同法第19条",
                "refs": ["evidence_1"],
            }
        ],
        binding_worker=BindingWorker(),
        review_worker=ReviewWorker(),
    )

    assert result.status == "partial_success"
    assert result.evidence_assessment["partially_sufficient"] is True
    assert len(result.review_findings) == 2
    assert result.review_findings[0]["judgment"] == "supported"
    assert result.review_findings[1]["judgment"] == "insufficient_evidence"
    assert "fallback_message" in result.answer_constraints
    payload = result.to_dict()
    assert payload["review_summary"]["target_count"] == 2
    assert payload["review_summary"]["matched_target_count"] == 1
    assert payload["review_summary"]["matched_target_refs"] == ["claim_1"]
    assert payload["review_summary"]["unsupported_target_refs"] == ["claim_2"]
    assert payload["review_summary"]["needs_more_evidence_targets"] == ["claim_2"]
    assert payload["review_summary"]["status_summary"] == "partial_success"
    assert payload["review_summary"]["review_mode"] == "challenge_review"
    assert payload["review_summary"]["review_confidence"] == "medium"
    assert payload["review_summary"]["review_scope"] == "multi_target"
    assert payload["review_summary"]["follow_up_retrieval_attempted"] is False
    assert result.evidence_assessment["missing_target_ratio"] == 0.5
    assert result.evidence_assessment["source_diversity"] == 1


def test_challenge_power_uses_follow_up_retrieval_when_more_evidence_is_needed() -> None:
    power = ChallengePower()
    retrieval = _FakeRetrievalPower()
    registry = _build_registry(review_worker=ReviewWorker(), retrieval_power=retrieval)

    result = power.execute(
        query="前两个结论的依据都对吗？",
        rewritten_query="请核验前两个结论的法条依据",
        candidate_targets=[
            {
                "object_id": "claim_1",
                "object_type": "claim",
                "content": "试用期最长一个月",
                "refs": ["evidence_1"],
            },
            {
                "object_id": "claim_2",
                "object_type": "claim",
                "content": "一年期合同试用期上限一个月",
                "refs": ["evidence_2"],
            },
        ],
        evidence_candidates=[
            {
                "object_id": "evidence_1",
                "object_type": "evidence_ref",
                "content": "劳动合同法第19条",
                "refs": ["evidence_1"],
            }
        ],
        binding_worker=BindingWorker(),
        review_worker=ReviewWorker(),
        retrieval_power=retrieval,
        worker_registry=registry,
    )

    assert result.status == "success"
    assert result.evidence_assessment["sufficient"] is True
    assert result.evidence_assessment["triggered_additional_retrieval"] is True
    assert result.evidence_assessment["follow_up_retrieval"]["attempted"] is True
    assert result.evidence_assessment["follow_up_retrieval"]["retrieved_evidence_count"] == 1
    assert result.evidence_assessment["retrieve_if_needed"]["needed"] is False
    payload = result.to_dict()
    assert payload["review_summary"]["matched_target_count"] == 2
    assert payload["review_summary"]["unsupported_target_refs"] == []
    assert payload["review_summary"]["review_mode"] == "challenge_review"
    assert payload["review_summary"]["review_confidence"] == "medium"
    assert payload["review_summary"]["review_scope"] == "multi_target"
    assert payload["review_summary"]["follow_up_retrieval_attempted"] is True
    assert payload["review_summary"]["follow_up_retrieval_improved"] is True
    assert payload["review_summary"]["follow_up_retrieval_sources"] == ["kb/law.md"]
    assert payload["review_summary"]["follow_up_retrieval_retrieved_evidence_count"] == 1
    assert retrieval.last_queries
    assert len(retrieval.last_queries) == 1
    assert retrieval.last_queries[0].startswith("请核验前两个结论的法条依据")
    assert "一年期合同试用期上限一个月" in retrieval.last_queries[0]
    assert "试用期最长一个月" not in retrieval.last_queries[0]


def test_challenge_power_follow_up_retrieval_targets_only_missing_target_refs() -> None:
    power = ChallengePower()
    retrieval = _FakeRetrievalPower()
    registry = _build_registry(review_worker=ReviewWorker(), retrieval_power=retrieval)

    result = power.execute(
        query="前两个结论的依据都对吗？",
        rewritten_query="请核验前两个结论的法条依据",
        candidate_targets=[
            {
                "object_id": "claim_1",
                "object_type": "claim",
                "content": "试用期最长一个月",
                "refs": ["evidence_1"],
            },
            {
                "object_id": "claim_2",
                "object_type": "claim",
                "content": "一年期合同试用期上限一个月",
                "refs": ["evidence_2", "section-19"],
            },
        ],
        evidence_candidates=[
            {
                "object_id": "evidence_1",
                "object_type": "evidence_ref",
                "content": "劳动合同法第19条",
                "refs": ["evidence_1"],
            }
        ],
        review_worker=ReviewWorker(),
        retrieval_power=retrieval,
        worker_registry=registry,
    )

    assert result.status == "success"
    assert result.evidence_assessment["follow_up_retrieval"]["attempted"] is True
    follow_up_units = result.evidence_assessment["follow_up_retrieval"]["query_units"]
    assert len(follow_up_units) == 1
    assert follow_up_units[0]["target_refs"] == ["evidence_2", "section-19"]


def test_challenge_result_can_convert_directly_to_review_bundle() -> None:
    power = ChallengePower()

    result = power.execute(
        query="你刚才这个依据是什么？",
        candidate_targets=[
            {
                "object_id": "claim_1",
                "object_type": "claim",
                "content": "试用期最长一个月",
                "refs": ["evidence_1"],
            }
        ],
        evidence_candidates=[
            {
                "object_id": "evidence_1",
                "object_type": "evidence_ref",
                "content": "劳动合同法第19条",
                "refs": ["evidence_1"],
            }
        ],
        binding_worker=BindingWorker(),
        review_worker=ReviewWorker(),
    )

    bundle = result.to_review_bundle()
    payload = bundle.to_dict()

    assert bundle.review_mode == "challenge_review"
    assert bundle.status == "success"
    assert isinstance(bundle.evidence_assessment_obj(), EvidenceAssessmentResult)
    assert bundle.evidence_assessment_obj().sufficient is True
    assert payload["review_summary"]["matched_target_refs"] == ["claim_1"]


def test_challenge_result_accessors_delegate_to_review_bundle_summary() -> None:
    result = ChallengeResult.from_review_evaluation(
        targets=(
            {"object_id": "claim_1"},
            {"object_id": "claim_2"},
        ),
        evidence_assessment=EvidenceAssessmentResult(
            partially_sufficient=True,
            matched_target_count=1,
            target_count=2,
            needs_more_evidence_targets=("claim_2",),
            follow_up_retrieval={
                "attempted": True,
                "improved": False,
                "source_refs": ["kb/law.md"],
                "retrieved_evidence_count": 1,
            },
        ),
        evaluation=ReviewEvaluationResult(
            status="partial_success",
            review_findings=(
                {"target_ref": "claim_1", "judgment": "supported"},
                {"target_ref": "claim_2", "judgment": "insufficient_evidence"},
            ),
            answer_constraints={"must_cite_sources": True},
        ),
        review_summary={},
    )

    summary_view = result.review_summary_view()

    assert result.matched_target_refs() == ("claim_1",)
    assert result.needs_more_evidence_targets() == ("claim_2",)
    assert result.follow_up_retrieval_attempted() is True
    assert summary_view.review_mode == "challenge_review"
    assert summary_view.follow_up_retrieval_attempted is True


def test_challenge_result_preserves_typed_evidence_assessment_in_to_dict() -> None:
    power = ChallengePower()

    result = power.execute(
        query="你刚才这个依据是什么？",
        candidate_targets=[
            {
                "object_id": "claim_1",
                "object_type": "claim",
                "content": "试用期最长一个月",
                "refs": ["evidence_1"],
            }
        ],
        evidence_candidates=[
            {
                "object_id": "evidence_1",
                "object_type": "evidence_ref",
                "content": "劳动合同法第19条",
                "refs": ["evidence_1"],
            }
        ],
        binding_worker=BindingWorker(),
        review_worker=ReviewWorker(),
    )

    assert isinstance(result.evidence_assessment_obj(), EvidenceAssessmentResult)
    payload = result.to_dict()
    assert payload["answer_constraints"] == result.answer_constraints
    assert payload["evidence_assessment"]["sufficient"] is True


def test_review_worker_evidence_check_returns_typed_assessment_result() -> None:
    worker = ReviewWorker()

    assessment = worker.evidence_check(
        query="你刚才这个依据是什么？",
        targets=[
            {
                "object_id": "claim_1",
                "object_type": "claim",
                "content": "试用期最长一个月",
                "refs": ["evidence_1"],
            }
        ],
        evidence_candidates=[
            {
                "object_id": "evidence_1",
                "object_type": "evidence_ref",
                "content": "劳动合同法第19条",
                "refs": ["evidence_1"],
            }
        ],
    )

    assert isinstance(assessment, EvidenceAssessmentResult)
    assert assessment.sufficient is True
    assert assessment.matched_target_count == 1
    assert assessment.needs_follow_up_retrieval() is False
    assert assessment.to_dict()["matched_target_refs"] == ["claim_1"]
    assert assessment.source_count == 1
    assert assessment.source_type_quality_band == "low"


def test_review_worker_re_evaluate_returns_typed_review_evaluation_result() -> None:
    worker = ReviewWorker()
    assessment = worker.evidence_check(
        query="你刚才这个依据是什么？",
        targets=[
            {
                "object_id": "claim_1",
                "object_type": "claim",
                "content": "试用期最长一个月",
                "refs": ["evidence_1"],
            }
        ],
        evidence_candidates=[
            {
                "object_id": "evidence_1",
                "object_type": "evidence_ref",
                "content": "劳动合同法第19条",
                "refs": ["evidence_1"],
            }
        ],
    )

    evaluation = worker.re_evaluate(
        query="你刚才这个依据是什么？",
        targets=[
            {
                "object_id": "claim_1",
                "object_type": "claim",
                "content": "试用期最长一个月",
                "refs": ["evidence_1"],
            }
        ],
        evidence_assessment=assessment,
        evidence_candidates=[
            {
                "object_id": "evidence_1",
                "object_type": "evidence_ref",
                "content": "劳动合同法第19条",
                "refs": ["evidence_1"],
            }
        ],
    )

    assert isinstance(evaluation, ReviewEvaluationResult)
    assert evaluation.status == "success"
    assert evaluation.review_findings[0]["judgment"] == "supported"


def test_challenge_result_can_be_built_from_typed_review_evaluation() -> None:
    challenge = ChallengeResult.from_review_evaluation(
        targets=(
            {"object_id": "claim_1"},
            {"object_id": "claim_2"},
        ),
        evidence_assessment={
            "partially_sufficient": True,
            "matched_target_count": 1,
            "needs_more_evidence_targets": ["claim_2"],
        },
        evaluation=ReviewEvaluationResult(
            status="partial_success",
            review_findings=(
                {"target_ref": "claim_1", "judgment": "supported"},
                {"target_ref": "claim_2", "judgment": "insufficient_evidence"},
            ),
            answer_constraints={"must_cite_sources": True},
        ),
    )

    assert challenge.status == "partial_success"
    assert isinstance(challenge.evidence_assessment_obj(), EvidenceAssessmentResult)
    bundle = challenge.to_review_bundle()
    assert bundle.review_mode == "challenge_review"
    assert bundle.matched_target_refs() == ("claim_1",)
    assert bundle.needs_more_evidence_targets() == ("claim_2",)


def test_typed_review_and_assessment_helpers_preserve_contract_updates() -> None:
    assessment = EvidenceAssessmentResult(
        partially_sufficient=True,
        supporting_evidence_refs=("evidence_1",),
        matched_target_count=1,
        target_count=2,
        needs_more_evidence_targets=("claim_2",),
    )
    updated_assessment = assessment.with_follow_up_retrieval(
        follow_up_retrieval={
            "attempted": True,
            "improved": True,
            "source_refs": ["kb/law.md"],
            "retrieved_evidence_count": 1,
        },
        triggered_additional_retrieval=True,
    )
    fallback_assessment = updated_assessment.with_fallback("evidence_fallback")

    evaluation = ReviewEvaluationResult(
        status="partial_success",
        review_findings=(
            {"target_ref": "claim_1", "judgment": "supported"},
            {"target_ref": "claim_2", "judgment": "insufficient_evidence"},
        ),
        answer_constraints={"must_cite_sources": True},
    )
    patched_evaluation = evaluation.with_answer_constraints(
        {
            "must_cite_sources": True,
            "fallback_message": "need more evidence",
        }
    )

    assert updated_assessment.follow_up_attempted() is True
    assert updated_assessment.follow_up_improved() is True
    assert updated_assessment.supporting_evidence_ref_list() == ["evidence_1"]
    assert updated_assessment.per_target_assessment_map() == {}
    assert fallback_assessment.fallback == "evidence_fallback"
    assert patched_evaluation.answer_constraints["fallback_message"] == "need more evidence"


def test_evidence_assessment_target_accessors_drive_review_lookup() -> None:
    assessment = EvidenceAssessmentResult(
        supporting_evidence_refs=("evidence_1", "evidence_2"),
        per_target_assessment=(
            {
                "target_ref": "claim_1",
                "matched": True,
                "matched_evidence_refs": ["evidence_1"],
            },
            {
                "target_ref": "claim_2",
                "matched": False,
                "matched_evidence_refs": [],
            },
        ),
    )

    assert assessment.target_is_matched("claim_1") is True
    assert assessment.target_is_matched("claim_2") is False
    assert assessment.matched_evidence_refs_for("claim_1") == ["evidence_1"]
    assert assessment.matched_evidence_refs_for("claim_missing") == []


def test_evidence_assessment_follow_up_accessors_drive_review_summary_fields() -> None:
    bundle = ChallengeResult.from_review_evaluation(
        targets=(
            {"object_id": "claim_1"},
            {"object_id": "claim_2"},
        ),
        evidence_assessment=EvidenceAssessmentResult(
            partially_sufficient=True,
            matched_target_count=1,
            target_count=2,
            needs_more_evidence_targets=("claim_2",),
            follow_up_retrieval={
                "attempted": True,
                "improved": True,
                "source_refs": ["kb/law.md"],
                "retrieved_evidence_count": 1,
            },
        ),
        evaluation=ReviewEvaluationResult(
            status="partial_success",
            review_findings=(
                {"target_ref": "claim_1", "judgment": "supported"},
                {"target_ref": "claim_2", "judgment": "insufficient_evidence"},
            ),
            answer_constraints={"must_cite_sources": True},
        ),
    ).to_review_bundle()

    assert bundle.follow_up_retrieval_attempted() is True
    assert bundle.follow_up_retrieval_improved() is True
    assert bundle.follow_up_retrieval_sources() == ("kb/law.md",)
    assert bundle.follow_up_retrieval_retrieved_evidence_count() == 1


def test_review_bundle_prefers_assessment_target_refs_over_review_findings_backfill() -> None:
    bundle = ChallengeResult.from_review_evaluation(
        targets=(
            {"object_id": "claim_1"},
            {"object_id": "claim_2"},
        ),
        evidence_assessment=EvidenceAssessmentResult(
            partially_sufficient=True,
            matched_target_count=1,
            target_count=2,
            matched_target_refs=("claim_1",),
            unsupported_target_refs=("claim_2",),
            needs_more_evidence_targets=("claim_2",),
        ),
        evaluation=ReviewEvaluationResult(
            status="partial_success",
            review_findings=(),
            answer_constraints={"must_cite_sources": True},
        ),
    ).to_review_bundle()

    assert bundle.matched_target_refs() == ("claim_1",)
    assert bundle.unsupported_target_refs() == ("claim_2",)
    assert bundle.needs_more_evidence_targets() == ("claim_2",)
    assert bundle.summary_view().matched_target_count == 1


def test_evidence_assessment_summary_view_and_review_bundle_can_reuse_assessment_counts() -> None:
    assessment = EvidenceAssessmentResult(
        partially_sufficient=True,
        matched_target_count=1,
        target_count=2,
        matched_target_refs=("claim_1",),
        unsupported_target_refs=("claim_2",),
        needs_more_evidence_targets=("claim_2",),
        follow_up_retrieval={
            "attempted": True,
            "improved": False,
        },
    )

    summary = assessment.summary_view()
    bundle = ChallengeResult.from_review_evaluation(
        targets=(),
        evidence_assessment=assessment,
        evaluation=ReviewEvaluationResult(
            status="partial_success",
            review_findings=(),
            answer_constraints={"must_cite_sources": True},
        ),
    ).to_review_bundle()

    assert summary.target_count == 2
    assert summary.matched_target_count == 1
    assert summary.unsupported_target_count == 1
    assert summary.needs_more_evidence_target_count == 1
    assert summary.follow_up_retrieval_attempted is True
    assert summary.follow_up_retrieval_improved is False
    assert bundle.target_count() == 2
    assert bundle.summary_view().follow_up_retrieval_attempted is True
