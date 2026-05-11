from __future__ import annotations

from intent import classify_intent


LAW_HISTORY = [
    {"role": "user", "content": "劳动合同法中试用期最长多久？"},
    {"role": "assistant", "content": "试用期最长可能为六个月，但要看合同期限。"},
]


def test_classifies_domain_question_as_qa() -> None:
    result = classify_intent("劳动合同法中试用期最长多久？")

    assert result.main_intent == "qa"
    assert result.modifiers.follow_up is False
    assert result.modifiers.challenge is False


def test_plain_greeting_is_chat_not_qa() -> None:
    result = classify_intent("你好")

    assert result.main_intent == "chat"
    assert result.modifiers.follow_up is False


def test_follow_up_uses_history_without_replacing_qa() -> None:
    result = classify_intent("那如果合同只有一年呢？", LAW_HISTORY)

    assert result.main_intent == "qa"
    assert result.modifiers.follow_up is True
    assert result.modifiers.challenge is False


def test_follow_up_marker_without_history_does_not_set_follow_up() -> None:
    result = classify_intent("那如果合同只有一年呢？")

    assert result.main_intent == "qa"
    assert result.modifiers.follow_up is False


def test_challenge_requires_previous_assistant_answer() -> None:
    result = classify_intent("你确定吗？", LAW_HISTORY)

    assert result.main_intent == "qa"
    assert result.modifiers.challenge is True
    assert result.modifiers.follow_up is True
    assert result.modifiers.needs_clarification is False


def test_challenge_without_history_needs_clarification() -> None:
    result = classify_intent("你确定吗？")

    assert result.main_intent == "chat"
    assert result.modifiers.challenge is False
    assert result.modifiers.needs_clarification is True


def test_ask_source_is_modifier_and_keeps_qa_with_history() -> None:
    result = classify_intent("依据是什么？", LAW_HISTORY)

    assert result.main_intent == "qa"
    assert result.modifiers.ask_source is True
    assert result.modifiers.follow_up is True


def test_ask_source_without_context_needs_clarification() -> None:
    result = classify_intent("依据是什么？")

    assert result.main_intent == "chat"
    assert result.modifiers.ask_source is True
    assert result.modifiers.needs_clarification is True


def test_ask_capability_routes_as_chat_modifier() -> None:
    result = classify_intent("你能做什么？")

    assert result.main_intent == "chat"
    assert result.modifiers.ask_capability is True


def test_out_of_scope_file_operation_is_not_qa() -> None:
    result = classify_intent("请删除知识库里的这个文件")

    assert result.main_intent == "chat"
    assert result.modifiers.out_of_scope is True


def test_challenge_and_ask_source_can_coexist() -> None:
    result = classify_intent("你刚才这个依据是什么，是不是不对？", LAW_HISTORY)

    assert result.main_intent == "qa"
    assert result.modifiers.challenge is True
    assert result.modifiers.ask_source is True
    assert result.modifiers.follow_up is True


def test_general_non_domain_question_stays_chat() -> None:
    result = classify_intent("周末有什么好玩的？")

    assert result.main_intent == "chat"
    assert result.modifiers.out_of_scope is False
