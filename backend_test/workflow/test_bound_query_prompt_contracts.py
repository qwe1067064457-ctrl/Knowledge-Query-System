from __future__ import annotations

from workflow.helpers.bound_query_prompt_helper import BoundQueryPromptHelper


def test_prompt_helper_validates_rewrite_payload_and_fallback_fields() -> None:
    helper = BoundQueryPromptHelper()

    rewrite_payload = helper.validate_rewrite_payload(
        {
            "resolved_target_ids": ["question_1", ""],
            "rewritten_query": "试用期依据是什么？",
            "confidence": "invalid",
            "needs_clarification": 0,
            "fallback_type": "needs_clarification",
            "reason": "multiple_relevant_targets",
        },
        original_query="那它的依据呢？",
    )

    assert rewrite_payload["resolved_target_ids"] == ["question_1"]
    assert rewrite_payload["rewritten_query"] == "试用期依据是什么？"
    assert rewrite_payload["confidence"] == "medium"
    assert rewrite_payload["needs_clarification"] is False
    assert rewrite_payload["fallback_type"] == "needs_clarification"
    assert rewrite_payload["reason"] == "multiple_relevant_targets"


def test_rewrite_prompt_contract_renders_required_sections() -> None:
    helper = BoundQueryPromptHelper()

    prompt = helper.render_rewrite_prompt(
        base_dir=None,
        query="那它的依据呢？",
        binding_context={
            "query_style": "follow_up",
            "candidate_count": 2,
            "relevant_target_ids": ["question_1"],
        },
        recent_messages=[
            {"role": "user", "content": "试用期依据是什么？"},
            {"role": "assistant", "content": "劳动合同法第19条。"},
        ],
        question_candidates=[{"object_id": "question_1", "content": "试用期依据是什么？"}],
    )

    assert "当前 state / 上下文摘要" in prompt
    assert "最近对话" in prompt
    assert "候选相关对象 / 候选问题对象" in prompt
    assert "resolved_target_ids" in prompt
    assert "needs_clarification" in prompt
    assert "fallback_type" in prompt
