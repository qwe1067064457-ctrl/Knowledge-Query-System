from __future__ import annotations

from workflow.types import EvidenceBundle, EvidenceItem
from workflow.workers.review_worker import ReviewWorker


def _bundle_with_quality(*, average_weighted_score: float, missing_evidence: bool, repaired_units: int) -> EvidenceBundle:
    return EvidenceBundle(
        query_unit_results=(
            {
                "unit_id": "primary",
                "query": "劳动合同法第19条怎么规定？",
                "origin": "primary",
                "quality": {"weighted_score": average_weighted_score},
                "evidence_count": 1,
                "repair_applied": repaired_units > 0,
                "repair_plan": {"enabled": repaired_units > 0},
                "repair_strategy": "expand_topk" if repaired_units > 0 else "none",
            },
        ),
        merged_evidence_items=(
            EvidenceItem(
                evidence_id="evidence_1",
                source_path="kb/law.md",
                source_type="official_structured",
                locator="section-19",
                snippet="一年期合同试用期上限一个月。",
                channel="vector",
                score=0.92,
                query_unit_ids=("primary",),
            ),
        ),
        source_refs=("kb/law.md",),
        coverage_summary={"query_units": 1, "sources": 1},
        quality_summary={
            "average_weighted_score": average_weighted_score,
            "status": "good" if average_weighted_score >= 0.75 else "weak",
            "repairable_units": 1 if repaired_units > 0 else 0,
            "repaired_units": repaired_units,
            "source_ref_count": 1,
            "merged_evidence_count": 1,
        },
        missing_evidence_notes=("retrieval_quality_weak",) if missing_evidence else (),
    )


def test_retrieval_quality_check_reports_summary_metrics() -> None:
    worker = ReviewWorker()
    bundle = _bundle_with_quality(average_weighted_score=0.91, missing_evidence=False, repaired_units=0)

    result = worker.retrieval_quality_check(evidence_bundle=bundle)

    assert result["status"] == "good"
    assert result["should_repair"] is False
    assert result["source_ref_count"] == 1


def test_retrieval_quality_check_reports_missing_evidence_and_repairable_state() -> None:
    worker = ReviewWorker()
    bundle = _bundle_with_quality(average_weighted_score=0.41, missing_evidence=True, repaired_units=1)

    result = worker.retrieval_quality_check(evidence_bundle=bundle)

    assert result["status"] == "weak"
    assert result["should_repair"] is True
    assert result["missing_evidence"] is True


def test_evidence_check_can_reuse_high_quality_existing_evidence_via_text_alignment() -> None:
    worker = ReviewWorker()

    assessment = worker.evidence_check(
        query="你刚才这个依据是什么？",
        targets=[
            {
                "object_id": "claim_1",
                "object_type": "answer_unit",
                "content": "一年期合同试用期上限一个月",
                "refs": [],
            }
        ],
        evidence_candidates=[
            {
                "object_id": "evidence_1",
                "object_type": "evidence_ref",
                "content": "劳动合同法第19条规定一年期合同试用期上限一个月。",
                "source_type": "official_structured",
                "channel": "vector",
                "refs": [],
            }
        ],
    )

    assert assessment.sufficient is True
    assert assessment.retrieve_if_needed["needed"] is False
    assert assessment.per_target_assessment[0]["matched_by"] == "text_alignment"
    assert assessment.per_target_assessment[0]["coverage_status"] == "supported"


def test_evidence_check_marks_related_but_not_grounded_existing_evidence_as_insufficient() -> None:
    worker = ReviewWorker()

    assessment = worker.evidence_check(
        query="你刚才这个依据是什么？",
        targets=[
            {
                "object_id": "claim_1",
                "object_type": "answer_unit",
                "content": "一年期合同试用期上限一个月",
                "refs": ["evidence_1"],
            }
        ],
        evidence_candidates=[
            {
                "object_id": "evidence_related",
                "object_type": "evidence_ref",
                "content": "一年期合同试用期上限一个月。",
                "source_type": "official_structured",
                "channel": "vector",
                "refs": [],
            }
        ],
    )

    assert assessment.sufficient is False
    assert assessment.retrieve_if_needed["needed"] is True
    assert assessment.retrieve_if_needed["reason"] == "related_evidence_not_grounded"
    assert assessment.evidence_notes == ("existing_evidence_related_but_not_grounded",)
    assert assessment.per_target_assessment[0]["matched_by"] == "text_related_only"
    assert assessment.per_target_assessment[0]["coverage_status"] == "related_only"
