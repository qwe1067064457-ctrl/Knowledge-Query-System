from __future__ import annotations

from intent import classify_intent


LAW_HISTORY = [
    {"role": "user", "content": "劳动合同法中试用期最长多久？"},
    {"role": "assistant", "content": "试用期最长可能为六个月，但要看合同期限。"},
]


def test_classifies_domain_question_as_simple_qa() -> None:
    result = classify_intent("劳动合同法中试用期最长多久？")

    assert result.resolved.main_intent == "qa"
    assert result.resolved.task.complexity == "simple"
    assert result.resolved.task.shape == "single_question"
    assert result.control.route == "rag"


def test_plain_greeting_is_chat() -> None:
    result = classify_intent("你好")

    assert result.resolved.main_intent == "chat"
    assert result.resolved.task.shape == "none"
    assert result.control.route == "chat"


def test_follow_up_uses_history_without_replacing_qa() -> None:
    result = classify_intent("那如果合同只有一年呢？", LAW_HISTORY)

    assert result.resolved.main_intent == "qa"
    assert result.resolved.modifiers.follow_up is True
    assert result.resolved.context_dependency == "history_reference"
    assert result.control.rewrite is True


def test_challenge_requires_previous_assistant_answer() -> None:
    result = classify_intent("你确定吗？", LAW_HISTORY)

    assert result.resolved.main_intent == "qa"
    assert result.resolved.modifiers.challenge is True
    assert result.resolved.context_dependency == "previous_answer"
    assert result.control.mode == "challenge"


def test_challenge_without_history_needs_clarification() -> None:
    result = classify_intent("你确定吗？")

    assert result.resolved.modifiers.challenge is False
    assert result.resolved.modifiers.needs_clarification is True
    assert result.control.route == "direct"
    assert result.control.mode == "clarify"


def test_ask_source_is_modifier_and_keeps_qa_with_history() -> None:
    result = classify_intent("依据是什么？", LAW_HISTORY)

    assert result.resolved.main_intent == "qa"
    assert result.resolved.modifiers.ask_source is True
    assert result.resolved.context_dependency == "previous_answer"


def test_ask_capability_routes_to_system() -> None:
    result = classify_intent("你能做什么？")

    assert result.resolved.main_intent == "system"
    assert result.control.route == "direct"
    assert result.control.mode == "capability"


def test_out_of_scope_file_operation_is_unsupported() -> None:
    result = classify_intent("请删除知识库里的这个文件")

    assert result.resolved.main_intent == "unsupported"
    assert result.resolved.modifiers.out_of_scope is True
    assert result.evidence.unsupported_signals["file_delete_request"] is True
    assert result.control.route == "reject"


def test_challenge_and_ask_source_can_coexist() -> None:
    result = classify_intent("你刚才这个依据是什么，是不是不对？", LAW_HISTORY)

    assert result.resolved.main_intent == "qa"
    assert result.resolved.modifiers.challenge is True
    assert result.resolved.modifiers.ask_source is True
    assert result.resolved.task.shape == "verify"


def test_multi_question_becomes_compound_and_decomposable() -> None:
    result = classify_intent("试用期最长多久？解除劳动合同怎么赔？")

    assert result.resolved.main_intent == "qa"
    assert result.resolved.task.complexity == "compound"
    assert result.resolved.task.shape == "multi_question"
    assert result.control.decompose_query is True


def test_complex_query_uses_agent_route() -> None:
    result = classify_intent("请对比三份制度差异并整理成表格")

    assert result.resolved.main_intent == "qa"
    assert result.resolved.task.complexity == "complex"
    assert result.resolved.task.shape == "compare"
    assert result.control.route == "agent"
    assert result.control.use_planner is True
    assert result.control.planning_level == "full"


def test_complex_summarize_query_uses_agent_without_explicit_planner() -> None:
    result = classify_intent("请总结这份制度的三点要点")

    assert result.resolved.main_intent == "qa"
    assert result.resolved.task.complexity == "complex"
    assert result.resolved.task.shape == "summarize"
    assert result.control.route == "agent"
    assert result.control.use_planner is False
    assert result.control.planning_level == "none"
    assert result.evidence.rule_confidence is not None


def test_enumerated_design_query_resolves_to_complex_mixed() -> None:
    result = classify_intent(
        "1. rule_id 是否完善 2. qa 不在知识库里怎么办 3. resolver 如何收敛 4. 用这条 query 走每一层",
        LAW_HISTORY,
    )

    assert result.resolved.main_intent == "qa"
    assert result.resolved.task.complexity == "complex"
    assert result.resolved.task.shape in {"mixed", "summarize", "compare", "verify"}
    assert result.control.route == "agent"
