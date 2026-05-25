from __future__ import annotations

from workflow.helpers.bound_query_prompt_helper import BoundQueryPromptHelper


def test_state_update_prompt_contract_renders_required_sections() -> None:
    helper = BoundQueryPromptHelper()

    prompt = helper.render_state_update_prompt(
        base_dir=None,
        query="那它的依据呢？",
        previous_state={
            "focus_question_object_id": "question_1",
            "focus_question_object_text": "试用期依据是什么？",
            "focus_predicate": "依据",
            "recent_question_objects": [{"object_id": "question_1", "content": "试用期依据是什么？"}],
            "recent_evidence_topics": ["劳动合同法第19条"],
            "resolution_confidence": "high",
            "last_update_reason": "previous_focus",
        },
        recent_messages=[
            {"role": "user", "content": "试用期依据是什么？"},
            {"role": "assistant", "content": "劳动合同法第19条。"},
        ],
        question_candidates=[{"object_id": "question_1", "content": "试用期依据是什么？"}],
        evidence_topics=["劳动合同法第19条"],
    )

    assert "上一轮状态" in prompt
    assert "最近对话" in prompt
    assert "候选问题对象" in prompt
    assert "候选证据主题" in prompt
    assert "focus_question_object_id" in prompt
    assert "resolution_confidence" in prompt


def test_prompt_helper_validates_state_update_payload_and_rewrite_payload() -> None:
    helper = BoundQueryPromptHelper()

    state_payload = helper.validate_state_update_payload(
        {
            "focus_question_object_id": "question_1",
            "focus_question_object_text": "试用期依据是什么？",
            "focus_predicate": "依据",
            "recent_question_objects": [
                {"object_id": "question_1", "content": "试用期依据是什么？"},
                {"object_id": "", "content": "bad"},
            ],
            "recent_evidence_topics": ["劳动合同法第19条", ""],
            "resolution_confidence": "invalid",
            "last_update_reason": "llm_update",
        }
    )
    rewrite_payload = helper.validate_rewrite_payload(
        {
            "resolved_target_ids": ["question_1", ""],
            "rewritten_query": "试用期依据是什么？",
            "confidence": "invalid",
            "needs_clarification": 0,
        },
        original_query="那它的依据呢？",
    )

    assert state_payload["resolution_confidence"] == "low"
    assert state_payload["recent_question_objects"] == [
        {"object_id": "question_1", "content": "试用期依据是什么？"}
    ]
    assert state_payload["recent_evidence_topics"] == ["劳动合同法第19条"]
    assert rewrite_payload["resolved_target_ids"] == ["question_1"]
    assert rewrite_payload["rewritten_query"] == "试用期依据是什么？"
    assert rewrite_payload["confidence"] == "medium"
    assert rewrite_payload["needs_clarification"] is False


def test_rewrite_prompt_contract_renders_required_sections() -> None:
    helper = BoundQueryPromptHelper()

    prompt = helper.render_rewrite_prompt(
        base_dir=None,
        query="那它的依据呢？",
        state={
            "focus_question_object_id": "question_1",
            "focus_question_object_text": "试用期依据是什么？",
            "focus_predicate": "依据",
            "recent_question_objects": [{"object_id": "question_1", "content": "试用期依据是什么？"}],
            "recent_evidence_topics": ["劳动合同法第19条"],
            "resolution_confidence": "high",
            "last_update_reason": "llm_update",
        },
        recent_messages=[
            {"role": "user", "content": "试用期依据是什么？"},
            {"role": "assistant", "content": "劳动合同法第19条。"},
        ],
        question_candidates=[{"object_id": "question_1", "content": "试用期依据是什么？"}],
    )

    assert "当前 state" in prompt
    assert "最近对话" in prompt
    assert "候选问题对象" in prompt
    assert "resolved_target_ids" in prompt
    assert "needs_clarification" in prompt
