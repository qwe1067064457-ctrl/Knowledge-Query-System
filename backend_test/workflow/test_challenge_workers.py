from __future__ import annotations

from workflow.orchestrated.execution_layer.workers.review.challenge_support_query_worker import (
    ChallengeSupportQueryWorker,
)
from workflow.orchestrated.execution_layer.workers.review.challenge_target_selection_worker import (
    ChallengeTargetSelectionWorker,
)
from workflow.types import ContextBindingResult


def test_challenge_target_selection_worker_prefers_binding_contract_targets() -> None:
    worker = ChallengeTargetSelectionWorker()

    binding_result = ContextBindingResult(
        relevant_set=(
            {
                "object_id": "claim_contract",
                "object_type": "answer_unit",
                "content": "A 结论",
                "refs": ["evidence_contract"],
            },
        ),
        bound_targets=(
            {
                "object_id": "claim_contract",
                "object_type": "answer_unit",
                "content": "A 结论",
                "refs": ["evidence_contract"],
            },
        ),
        resolved_target_ids=("claim_contract",),
    )

    result = worker.run(
        candidate_targets=[{"object_id": "claim_other", "content": "B 结论"}],
        evidence_candidates=[],
        binding_result=binding_result.to_dict(),
    )

    assert result["binding_contract_used"] is True
    assert result["needs_clarification"] is False
    assert result["targets"][0]["object_id"] == "claim_contract"


def test_challenge_target_selection_worker_marks_clarification_when_binding_is_ambiguous() -> None:
    worker = ChallengeTargetSelectionWorker()

    binding_result = ContextBindingResult(
        relevant_set=(
            {"object_id": "claim_a", "content": "A 结论"},
            {"object_id": "claim_b", "content": "B 结论"},
        ),
        needs_clarification=True,
        binding_ambiguous=True,
        fallback_type="needs_clarification",
        clarification_hint="请明确你是在问 A 还是 B。",
    )

    result = worker.run(
        candidate_targets=[],
        evidence_candidates=[],
        binding_result=binding_result,
    )

    assert result["needs_clarification"] is True
    assert result["clarification_hint"] == "请明确你是在问 A 还是 B。"
    assert len(result["clarification_targets"]) == 2


def test_challenge_support_query_worker_builds_only_missing_target_units() -> None:
    worker = ChallengeSupportQueryWorker()

    result = worker.run(
        query="请核验前两个结论的法条依据",
        targets=[
            {"object_id": "claim_1", "content": "试用期最长一个月", "refs": ["evidence_1"]},
            {"object_id": "claim_2", "content": "一年期合同试用期上限一个月", "refs": ["evidence_2", "section-19"]},
        ],
        requested_target_refs=["evidence_2"],
    )

    query_units = result["query_units"]
    assert len(query_units) == 1
    assert query_units[0]["target_refs"] == ["evidence_2", "section-19"]
    assert "一年期合同试用期上限一个月" in query_units[0]["text"]


def test_challenge_support_query_worker_returns_empty_when_requested_refs_do_not_match() -> None:
    worker = ChallengeSupportQueryWorker()

    result = worker.run(
        query="请核验这个结论",
        targets=[{"object_id": "claim_1", "content": "试用期最长一个月", "refs": ["evidence_1"]}],
        requested_target_refs=["evidence_missing"],
    )

    assert result["query_units"] == []
