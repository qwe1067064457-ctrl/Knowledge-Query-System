from __future__ import annotations

from workflow.powers.challenge_power import ChallengePower
from workflow.types import ContextBindingResult
from workflow.workers.binding_worker import BindingWorker
from workflow.workers.review_worker import ReviewWorker


def test_challenge_power_prefers_binding_contract_targets_over_worker_rebinding() -> None:
    power = ChallengePower()

    binding_result = ContextBindingResult(
        relevant_set=(
            {
                "object_id": "claim_contract",
                "object_type": "answer_unit",
                "content": "ChallengePower 还没完全统一进 Context Binding V2 contract。",
                "refs": ["evidence_contract"],
            },
        ),
        bound_targets=(
            {
                "object_id": "claim_contract",
                "object_type": "answer_unit",
                "content": "ChallengePower 还没完全统一进 Context Binding V2 contract。",
                "refs": ["evidence_contract"],
            },
        ),
        resolved_target_ids=("claim_contract",),
        binding_confidence="high",
        matched_by="llm_resolution",
    )

    result = power.execute(
        query="你刚才说 challenge 还没完全统一，这个依据是什么？",
        candidate_targets=[],
        binding_result=binding_result,
        evidence_candidates=[
            {
                "object_id": "evidence_contract",
                "object_type": "evidence_ref",
                "content": "challenge 内部仍在走旧 binding_worker.bind 路径。",
                "refs": ["evidence_contract"],
            }
        ],
        binding_worker=BindingWorker(),
        review_worker=ReviewWorker(),
    )

    assert result.status == "success"
    assert result.targets[0]["object_id"] == "claim_contract"
    assert result.review_summary["binding_contract_used"] is True


def test_challenge_power_uses_binding_contract_clarification_when_binding_requires_it() -> None:
    power = ChallengePower()

    binding_result = ContextBindingResult(
        relevant_set=(
            {"object_id": "claim_a", "object_type": "answer_unit", "content": "A 结论"},
            {"object_id": "claim_b", "object_type": "answer_unit", "content": "B 结论"},
        ),
        binding_confidence="low",
        binding_ambiguous=True,
        needs_clarification=True,
        fallback_type="needs_clarification",
        reason="multiple_relevant_targets",
        clarification_hint="请明确你是在问 A 结论还是 B 结论。",
    )

    result = power.execute(
        query="这个说法依据是什么？",
        candidate_targets=[],
        binding_result=binding_result,
        evidence_candidates=[],
        binding_worker=BindingWorker(),
        review_worker=ReviewWorker(),
    )

    assert result.status == "needs_clarification"
    assert result.answer_constraints["clarification_question"] == "请明确你是在问 A 结论还是 B 结论。"
    assert result.review_summary["binding_contract_used"] is True
    assert result.review_summary["binding_fallback_type"] == "needs_clarification"
