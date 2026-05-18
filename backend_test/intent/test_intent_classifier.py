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
    assert result.resolved.task.topology == "parallel_queries"
    assert result.control.decompose_query is True


def test_sequence_words_count_as_multi_question() -> None:
    result = classify_intent("第一，试用期最长多久？第二，公司解除合同要赔吗？")

    assert result.resolved.main_intent == "qa"
    assert result.resolved.task.complexity == "compound"
    assert result.resolved.task.shape == "multi_question"
    assert result.resolved.task.topology == "parallel_queries"


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


def test_enumerated_design_query_prefers_compound_over_mixed_complex() -> None:
    result = classify_intent(
        "1. rule_id 是否完善 2. qa 不在知识库里怎么办 3. resolver 如何收敛 4. 用这条 query 走每一层",
        LAW_HISTORY,
    )

    assert result.resolved.main_intent == "qa"
    assert result.resolved.task.complexity == "compound"
    assert result.resolved.task.shape == "multi_question"
    assert result.resolved.task.topology == "parallel_queries"
    assert result.control.route == "rag"


def test_meta_analysis_query_stays_qa_not_chat() -> None:
    result = classify_intent("我是想看代码解析，不看它做了什么，这个 query 我现在的规则能做好的判断吗？")

    assert result.resolved.main_intent == "qa"
    assert result.control.route == "rag"


def test_generic_qa_supervision_sample_hits_generic_rule() -> None:
    result = classify_intent("如果公司拖欠工资，我可以怎么处理？")

    assert "intent.qa.generic" in {match.rule_id for match in result.evidence.matched_rules}
    assert "intent.qa.judgment" not in {match.rule_id for match in result.evidence.matched_rules}


def test_judgment_qa_supervision_sample_hits_judgment_rule() -> None:
    result = classify_intent("这样算医疗事故吗？")

    assert "intent.qa.judgment" in {match.rule_id for match in result.evidence.matched_rules}


def test_soft_doubt_supervision_sample_hits_soft_doubt_rule() -> None:
    result = classify_intent(
        "这个说法是不是太绝对了？",
        [{"role": "assistant", "content": "这种情况一定要赔偿。"}],
    )

    assert "challenge.soft_doubt" in {match.rule_id for match in result.evidence.matched_rules}


def test_generic_qa_how_to_calculate_hits_generic_rule() -> None:
    result = classify_intent("医保报销比例如何计算？")

    assert "intent.qa.generic" in {match.rule_id for match in result.evidence.matched_rules}


def test_generic_qa_how_to_determine_hits_generic_rule() -> None:
    result = classify_intent("赔偿金额通常如何确定？")

    assert "intent.qa.generic" in {match.rule_id for match in result.evidence.matched_rules}


def test_generic_qa_how_to_apply_hits_generic_rule() -> None:
    result = classify_intent("工伤认定一般怎么申请？")

    assert "intent.qa.generic" in {match.rule_id for match in result.evidence.matched_rules}


def test_generic_qa_self_contained_consequence_question_avoids_missing_history() -> None:
    result = classify_intent("这种情况通常会有什么后果？")

    matched_rule_ids = {match.rule_id for match in result.evidence.matched_rules}
    assert "intent.qa.generic" in matched_rule_ids
    assert "context.follow_up.missing_history" not in matched_rule_ids


def test_soft_doubt_confirm_no_exception_hits_soft_doubt_rule() -> None:
    result = classify_intent(
        "你确定没有例外情况吗？",
        [{"role": "assistant", "content": "这个规则在所有情况下都适用。"}],
    )

    assert "challenge.soft_doubt" in {match.rule_id for match in result.evidence.matched_rules}


def test_soft_doubt_can_follow_previous_absolute_answer() -> None:
    result = classify_intent(
        "这个规则我有点没看懂，你是说在任何情况下都适用吗？",
        [{"role": "assistant", "content": "这种规则在任何情况下都适用。"}],
    )

    assert "challenge.soft_doubt" in {match.rule_id for match in result.evidence.matched_rules}


def test_soft_doubt_exception_probe_hits_soft_doubt_rule() -> None:
    result = classify_intent(
        "难道就没有别的例外吗？",
        [{"role": "assistant", "content": "这里没有任何例外。"}],
    )

    assert "challenge.soft_doubt" in {match.rule_id for match in result.evidence.matched_rules}


def test_self_contained_judgment_question_avoids_missing_history() -> None:
    result = classify_intent("这种情况会被认定为工伤吗？")

    matched_rule_ids = {match.rule_id for match in result.evidence.matched_rules}
    assert "intent.qa.judgment" in matched_rule_ids
    assert "context.follow_up.missing_history" not in matched_rule_ids


def test_long_explanatory_qa_with_whether_clause_does_not_hit_judgment() -> None:
    result = classify_intent(
        "我们之前讨论了公司在合同履行过程中可能承担的违约责任。现在我想更系统地理解一下："
        "在我国合同法体系下，如果一方延迟履行义务但最终仍然履行完成，另一方主张违约责任时"
        "通常可以请求哪些救济方式？是否包括实际履行、违约金以及损害赔偿？"
    )

    matched_rule_ids = {match.rule_id for match in result.evidence.matched_rules}
    assert "intent.qa.generic" in matched_rule_ids
    assert "intent.qa.judgment" not in matched_rule_ids


def test_risk_classification_question_hits_judgment_rule() -> None:
    result = classify_intent(
        "在一个知识问答系统中，如果检索结果来自两条互相矛盾的法规解释，而系统只返回其中一条，"
        "是否可以认为系统存在误导性输出的风险？"
    )

    assert "intent.qa.judgment" in {match.rule_id for match in result.evidence.matched_rules}


def test_self_contained_major_fault_question_hits_judgment_rule() -> None:
    result = classify_intent(
        "如果开发团队明知模型存在明显的 hallucination 风险，但仍然将其用于自动生成法律建议，"
        "这种行为是否可能构成重大过失？"
    )

    matched_rule_ids = {match.rule_id for match in result.evidence.matched_rules}
    assert "intent.qa.judgment" in matched_rule_ids
    assert "context.follow_up.missing_history" not in matched_rule_ids


def test_soft_doubt_uncertain_follow_up_hits_soft_doubt_rule() -> None:
    result = classify_intent(
        "你刚才说在这种情况下法院通常会支持违约金请求，但我有点不确定，是不是还需要考虑违约金是否明显过高的问题？",
        [{"role": "assistant", "content": "这种情况下法院通常会支持违约金请求。"}],
    )

    matched_rule_ids = {match.rule_id for match in result.evidence.matched_rules}
    assert "challenge.soft_doubt" in matched_rule_ids
    assert "intent.qa.judgment" not in matched_rule_ids


def test_soft_doubt_bias_check_hits_soft_doubt_rule() -> None:
    result = classify_intent(
        "如果按照你前面的解释，似乎只要存在因果关系就可以认定侵权。但我理解中好像还需要有主观过错，这里是不是我理解有偏差？",
        [{"role": "assistant", "content": "只要存在因果关系就可以认定侵权。"}],
    )

    assert "challenge.soft_doubt" in {match.rule_id for match in result.evidence.matched_rules}


def test_soft_doubt_misclassification_probe_hits_soft_doubt_rule() -> None:
    result = classify_intent(
        "你前面提到系统可以通过规则层解决大部分意图分类问题。但如果遇到比较模糊的表达，比如既有质疑又有求证，这种规则是否会误判？",
        [{"role": "assistant", "content": "规则层可以解决大部分意图分类问题。"}],
    )

    assert "challenge.soft_doubt" in {match.rule_id for match in result.evidence.matched_rules}


def test_soft_doubt_idealized_boundary_hits_soft_doubt_not_judgment() -> None:
    result = classify_intent(
        "按照你给的分层策略，intent.qa.judgment 和 intent.qa.generic 区别主要在于是否包含判断性表达，"
        "但在一些复杂场景里两者好像界限并不绝对，这样的区分会不会有点过于理想化？",
        [{"role": "assistant", "content": "两者的区别主要在于是否包含判断性表达。"}],
    )

    matched_rule_ids = {match.rule_id for match in result.evidence.matched_rules}
    assert "challenge.soft_doubt" in matched_rule_ids
    assert "intent.qa.judgment" not in matched_rule_ids


def test_explanatory_penalty_query_stays_generic_not_judgment() -> None:
    result = classify_intent(
        "假设一个企业在数据出境时未进行安全评估，但数据规模较小，且未造成实际损害。根据现行法规，"
        "这种行为是否属于行政违法？一般会面临什么类型的处罚？"
    )

    matched_rule_ids = {match.rule_id for match in result.evidence.matched_rules}
    assert "intent.qa.generic" in matched_rule_ids or result.resolved.main_intent == "qa"
    assert "intent.qa.judgment" not in matched_rule_ids


def test_soft_doubt_implication_perf_probe_hits_soft_doubt_rule() -> None:
    result = classify_intent(
        "我在想，你说的“会话恢复”是按需从磁盘重建对象，那是不是意味着在高并发场景下可能会出现性能瓶颈？",
        [{"role": "assistant", "content": "会话恢复是按需从磁盘重建对象。"}],
    )

    assert "challenge.soft_doubt" in {match.rule_id for match in result.evidence.matched_rules}


def test_soft_doubt_authorization_scope_probe_is_not_privileged_operation() -> None:
    result = classify_intent(
        "你前面说这种授权链路只要有一次用户确认就够了，但我有点拿不准，是不是还得区分后续用途有没有超出原始授权范围？",
        [{"role": "assistant", "content": "这种授权链路只要有一次用户确认，通常就可以覆盖后续处理。"}],
    )

    matched_rule_ids = {match.rule_id for match in result.evidence.matched_rules}
    assert "challenge.soft_doubt" in matched_rule_ids
    assert "unsupported.privileged_operation" not in matched_rule_ids


def test_soft_doubt_cautious_understanding_probe_hits_soft_doubt_rule() -> None:
    result = classify_intent(
        "按你刚才那个判断逻辑，似乎只要留痕完整就能证明合规。可我理解里好像还得看留痕内容本身是不是充分，这里是不是我理解得更谨慎一些？",
        [{"role": "assistant", "content": "只要留痕完整，就能证明整体流程合规。"}],
    )

    assert "challenge.soft_doubt" in {match.rule_id for match in result.evidence.matched_rules}


def test_soft_doubt_weak_signal_ignored_probe_hits_soft_doubt_rule() -> None:
    result = classify_intent(
        "按照你刚才的说法，这类输出风险主要靠 route 控制来兜住。我不太确定，这会不会让 evidence 层里的一些弱信号被忽略掉？",
        [{"role": "assistant", "content": "这类输出风险主要还是靠 route 控制来兜底。"}],
    )

    assert "challenge.soft_doubt" in {match.rule_id for match in result.evidence.matched_rules}


def test_generic_explanatory_penalty_question_hits_generic_rule() -> None:
    result = classify_intent(
        "假设一个企业在数据出境时未进行安全评估，但数据规模较小，且未造成实际损害。根据现行法规，"
        "这种行为是否属于行政违法？一般会面临什么类型的处罚？"
    )

    matched_rule_ids = {match.rule_id for match in result.evidence.matched_rules}
    assert "intent.qa.generic" in matched_rule_ids


def test_generic_architecture_design_question_hits_generic_rule() -> None:
    result = classify_intent(
        "我们正在设计一个多租户知识库系统。从架构角度看，session 隔离是否必须依赖 group_id？"
        "如果系统未来扩展为 SaaS 多企业版本，session 主键设计应该考虑哪些因素？"
    )

    matched_rule_ids = {match.rule_id for match in result.evidence.matched_rules}
    assert "intent.qa.generic" in matched_rule_ids


def test_judgment_question_does_not_also_hit_generic_rule() -> None:
    result = classify_intent(
        "某电商平台未经用户明确同意，将用户购买记录用于精准广告推荐，但未泄露给第三方，"
        "这种行为是否违反个人信息保护法？"
    )

    matched_rule_ids = {match.rule_id for match in result.evidence.matched_rules}
    assert "intent.qa.judgment" in matched_rule_ids
    assert "intent.qa.generic" not in matched_rule_ids


def test_soft_doubt_follow_up_does_not_also_hit_generic_rule() -> None:
    result = classify_intent(
        "你刚才说在这种情况下法院通常会支持违约金请求，但我有点不确定，是不是还需要考虑违约金是否明显过高的问题？",
        [{"role": "assistant", "content": "在这种情况下，法院通常会支持违约金请求。"}],
    )

    matched_rule_ids = {match.rule_id for match in result.evidence.matched_rules}
    assert "challenge.soft_doubt" in matched_rule_ids
    assert "intent.qa.generic" not in matched_rule_ids


def test_parallel_subtasks_stay_compound_instead_of_becoming_complex() -> None:
    result = classify_intent("请分别说明试用期的条件、流程、时限。")

    assert result.resolved.main_intent == "qa"
    assert result.resolved.task.complexity == "compound"
    assert result.resolved.task.topology == "parallel_subtasks"
    assert result.control.route == "rag"
    assert result.control.decompose_query is True


def test_answer_structure_request_is_not_misclassified_as_staged_task() -> None:
    result = classify_intent("请先说是否成立，再说依据，再说风险。")

    assert result.resolved.task.topology != "staged"
    assert result.control.route != "agent"


def test_explicit_staged_task_is_marked_as_staged_complex() -> None:
    result = classify_intent("请先判断是否成立，再说明依据，最后给出风险提示。")

    assert result.resolved.main_intent == "qa"
    assert result.resolved.task.complexity == "complex"
    assert result.resolved.task.topology == "staged"
    assert result.control.route == "agent"
