from __future__ import annotations

from workflow.powers.challenge_power import ChallengePower
from workflow.types import EvidenceBundle, EvidenceItem
from workflow.workers.binding_worker import BindingWorker
from workflow.workers.review_worker import ReviewWorker


class _FakeRetrievalPower:
    def retrieve(self, query_units, *, top_k: int = 4) -> EvidenceBundle:
        del top_k
        assert query_units
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


def test_challenge_power_uses_follow_up_retrieval_when_more_evidence_is_needed() -> None:
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
        retrieval_power=_FakeRetrievalPower(),
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
    assert payload["review_summary"]["matched_target_refs"] == ["claim_1"]
