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


def test_soft_challenge_phrase_is_recognized_with_history() -> None:
    result = classify_intent("这个说法太绝对了吧？", LAW_HISTORY)

    assert result.resolved.main_intent == "qa"
    assert result.resolved.modifiers.soft_doubt is True
    assert result.resolved.modifiers.challenge is False
    assert result.control.mode == "normal"


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


def test_sequence_words_count_as_multi_question() -> None:
    result = classify_intent("第一，试用期最长多久？第二，公司解除合同要赔吗？")

    assert result.resolved.main_intent == "qa"
    assert result.resolved.task.complexity in {"compound", "complex"}
    assert result.resolved.task.shape in {"multi_question", "mixed", "verify"}


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


def test_judgment_style_fuzzy_qa_routes_to_clarify_not_chat() -> None:
    result = classify_intent("这样算不算医疗事故？")

    assert result.resolved.main_intent == "qa"
    assert result.resolved.modifiers.needs_clarification is True
    assert result.control.route == "direct"
    assert result.control.mode == "clarify"


def test_cost_focused_judgment_query_stays_qa() -> None:
    result = classify_intent("我想先确认一个定义问题：这样算不算医疗事故？背景情况很多，但核心只是确认这个概念本身怎么定义。")

    assert result.resolved.main_intent == "qa"
    assert result.control.route == "rag"


def test_explicit_judgment_qa_stays_rag_instead_of_clarify() -> None:
    result = classify_intent("电子合同是否具有法律效力？")

    assert result.resolved.main_intent == "qa"
    assert result.resolved.modifiers.needs_clarification is False
    assert result.control.route == "rag"


def test_generic_qa_rescue_keeps_plain_legal_question_out_of_chat() -> None:
    result = classify_intent("刑事拘留最长多少天？")

    assert result.resolved.main_intent == "qa"
    assert result.control.route == "rag"


def test_generic_self_anchor_question_stays_qa() -> None:
    result = classify_intent("这算重大疾病吗？")

    assert result.resolved.main_intent == "qa"
    assert result.control.route in {"rag", "direct"}


def test_long_meta_like_query_stays_complex_qa() -> None:
    result = classify_intent(
        "你刚才说医疗过失需要证明因果关系，那具体举证责任是怎么分配的？另外，你这个结论是不是基于某个司法解释？如果有的话能具体说明吗？"
    )

    assert result.resolved.main_intent == "qa"
    assert result.resolved.task.complexity == "complex"
    assert result.control.route == "agent"


def test_long_verify_query_prefers_verify_shape_and_agent_route() -> None:
    result = classify_intent(
        "我和公司签了三年劳动合同，现在工作一年多，公司说我绩效不达标，准备解除合同。但合同里没有明确绩效考核标准，也没有具体说明不达标的界定方式。我想知道，这种情况下公司单方面解除是否合法？如果不合法，我可以主张什么权利？"
    )

    assert result.resolved.main_intent == "qa"
    assert result.resolved.task.complexity == "complex"
    assert result.resolved.task.shape == "verify"
    assert result.control.route == "agent"


def test_long_verify_plus_tail_summary_query_becomes_mixed() -> None:
    result = classify_intent(
        "你之前说这种情况一定要承担赔偿责任，但我查到有案例法院并未支持赔偿请求。你的结论是否基于特定条件？如果条件不同，是否会得出不同结果？请按步骤整理关键事实、争议点和判断依据。"
    )

    assert result.resolved.main_intent == "qa"
    assert result.resolved.task.complexity == "complex"
    assert result.resolved.task.shape == "mixed"
    assert result.control.route == "agent"


def test_follow_up_missing_history_does_not_override_self_explanatory_qa() -> None:
    result = classify_intent("如果没有证据怎么办？")

    assert result.resolved.main_intent == "qa"
    assert result.control.route != "chat"


def test_enumerated_design_query_resolves_to_complex_mixed() -> None:
    result = classify_intent(
        "1. rule_id 是否完善 2. qa 不在知识库里怎么办 3. resolver 如何收敛 4. 用这条 query 走每一层",
        LAW_HISTORY,
    )

    assert result.resolved.main_intent == "qa"
    assert result.resolved.task.complexity == "complex"
    assert result.resolved.task.shape in {"mixed", "summarize", "compare", "verify"}
    assert result.control.route == "agent"


def test_meta_analysis_query_stays_qa_not_chat() -> None:
    result = classify_intent("我是想看代码解析，不看它做了什么，这个 query 我现在的规则能做好的判断吗？")

    assert result.resolved.main_intent == "qa"
    assert result.control.route == "rag"
