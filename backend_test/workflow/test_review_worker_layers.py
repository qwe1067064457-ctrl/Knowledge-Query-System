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
