from __future__ import annotations

import re
from typing import Any, Iterable, Pattern

from intent.control_signal import build_control_signal
from intent.rule_assets import (
    ASK_SOURCE_PATTERNS,
    CAPABILITY_PATTERNS,
    CHALLENGE_PATTERNS,
    CHAT_PATTERNS,
    DOMAIN_HINT_TOKENS,
    DOMAIN_QA_PATTERNS,
    FOLLOW_UP_PATTERNS,
    JUDGMENT_QA_PATTERNS,
    META_ANALYSIS_QA_PATTERNS,
    SELF_ANCHOR_TOKENS,
)
from intent.rule_confidence import calculate_rule_confidence
from intent.resolver import resolve_intent
from intent.types import (
    CandidateIntent,
    ClassifierMode,
    ContextSignals,
    ContextState,
    IntentAnalysis,
    IntentEvidence,
    IntentInput,
    IntentModifiers,
    ModelContext,
    RuleMatch,
    SignalBuckets,
    TaskCandidate,
)


RULE_STRENGTH_SCORES = {"high": 0.9, "medium": 0.6, "low": 0.3}
UNSUPPORTED_RULES: tuple[tuple[str, Pattern[str], str], ...] = (
    (
        "unsupported.file_delete_request",
        re.compile(r"(删除|移除|清空).{0,12}(文件|文档|资料|知识库|目录|数据|记录)", re.IGNORECASE),
        "file_delete_request",
    ),
    (
        "unsupported.file_write_request",
        re.compile(r"(修改|更新|覆盖|写入).{0,12}(文件|文档|资料|知识库|目录|数据|记录)", re.IGNORECASE),
        "file_write_request",
    ),
    (
        "unsupported.kb_admin_request",
        re.compile(r"(上传|导入|新增|新建|创建).{0,12}(知识库|资料|文档|文件)", re.IGNORECASE),
        "kb_admin_request",
    ),
    (
        "unsupported.privileged_operation",
        re.compile(r"(授权|审批|管理员|权限变更)", re.IGNORECASE),
        "privileged_operation",
    ),
    (
        "unsupported.unknown_external_action",
        re.compile(r"(帮我操作|替我执行|调用外部系统)", re.IGNORECASE),
        "unknown_external_action",
    ),
)
MULTI_QUESTION_PATTERNS: tuple[Pattern[str], ...] = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"\?.+\?",
        r"？.+？",
        r"^\s*1\.",
        r"(首先|其次|第一|第二|第三|最后|还有就是|一方面|另一方面)",
        r"(\d\.|[①②③④⑤]).+?(\d\.|[①②③④⑤])",
        r"[；;].*?[？?]",
        r"[？?].{0,20}(另外|还有|以及|同时).{0,20}[？?]",
    )
)
GENERIC_QA_PATTERNS: tuple[Pattern[str], ...] = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"(怎么(办|处理|解决)|如何(申请|办理|认定|处理|解决)|有哪些(要求|条件|风险|责任)|能不能|会.{0,6}(什么后果|怎样)|要赔吗|有责任吗|合法吗|违法吗|有效吗|对吗|有问题吗|区别是什么|最长多少天|承担哪些法律责任)",
    )
)
COMPLEX_TASK_PATTERNS: tuple[Pattern[str], ...] = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"对比|比较|差异|异同",
        r"总结|归纳|提炼|整理",
        r"验证|核对|判断对错|逐条分析|举证责任|因果关系",
        r"表格|清单|分步骤|逐层|结构化|决策树|分析框架",
        r"如何收敛|合理性评估|每一层|走一遍|设计说明|关键事实|争议点|判断依据",
    )
)


def classify_intent(
    message: str,
    history: Iterable[dict[str, Any]] | None = None,
) -> IntentAnalysis:
    history_items = list(history or [])
    normalized = _normalize(message)
    intent_input = IntentInput(
        user_query=normalized,
        context_state=_build_context_state(history_items),
        model_context=_build_model_context(history_items),
    )
    evidence = _build_rule_evidence(intent_input, history_items)
    resolved = resolve_intent(evidence)
    control = build_control_signal(resolved)
    return IntentAnalysis(
        input=intent_input,
        evidence=evidence,
        resolved=resolved,
        control=control,
    )


def _build_context_state(history: list[dict[str, Any]]) -> ContextState:
    has_previous_answer = any(
        item.get("role") == "assistant" and str(item.get("content", "")).strip()
        for item in history
    )
    return ContextState(
        has_history=bool(history),
        has_previous_answer=has_previous_answer,
        last_main_intent=_history_last_main_intent(history),
    )


def _build_model_context(history: list[dict[str, Any]]) -> ModelContext:
    last_user_query = ""
    last_answer_summary = ""
    last_retrieval_summary = ""
    for item in reversed(history):
        role = item.get("role")
        content = str(item.get("content", "")).strip()
        if role == "assistant" and not last_answer_summary and content:
            last_answer_summary = content[:200]
        elif role == "user" and not last_user_query and content:
            last_user_query = content[:200]
        if item.get("retrieval_steps") and not last_retrieval_summary:
            last_retrieval_summary = "has_retrieval_steps"
        if last_user_query and last_answer_summary and last_retrieval_summary:
            break
    return ModelContext(
        last_user_query=last_user_query,
        last_answer_summary=last_answer_summary,
        last_retrieval_summary=last_retrieval_summary,
    )


def _build_rule_evidence(intent_input: IntentInput, history: list[dict[str, Any]]) -> IntentEvidence:
    text = intent_input.user_query
    ctx = intent_input.context_state

    matched_rules: list[RuleMatch] = []
    intent_signals: list[str] = []
    task_signals: list[str] = []
    context_signals: list[str] = []
    safety_signals: list[str] = []
    unsupported_signals = {
        "file_write_request": False,
        "file_delete_request": False,
        "kb_admin_request": False,
        "privileged_operation": False,
        "unknown_external_action": False,
    }
    dependency_signals = {
        "none": False,
        "history_reference": False,
        "previous_answer": False,
        "previous_retrieval": False,
        "ambiguous": False,
    }

    domain_qa = _matches(text, DOMAIN_QA_PATTERNS)
    chat = _matches(text, CHAT_PATTERNS)
    ask_capability = _matches(text, CAPABILITY_PATTERNS)
    ask_source = _matches(text, ASK_SOURCE_PATTERNS)
    judgment_qa = _looks_like_judgment_qa(text)
    generic_qa = _looks_like_generic_qa(text)
    hard_challenge_requested = _matches(text, CHALLENGE_PATTERNS)
    soft_challenge_requested = _looks_like_soft_challenge(text)
    challenge_requested = hard_challenge_requested or soft_challenge_requested
    follow_up_requested = _matches(text, FOLLOW_UP_PATTERNS)
    multi_question = _is_multi_question(text)
    qa_signal_detected = (
        domain_qa
        or judgment_qa
        or generic_qa
        or ask_source
        or challenge_requested
        or _contains_domain_hint(text)
        or _question_phrase_count(text) >= 1
    )
    long_complex_fallback = _should_force_complex_qa(text, qa_signal_detected)
    complex_task = _matches(text, COMPLEX_TASK_PATTERNS) or _looks_like_design_review_query(text) or long_complex_fallback

    if domain_qa or judgment_qa or generic_qa:
        _append_signal(intent_signals, "qa")
        if generic_qa and not (domain_qa or judgment_qa):
            rule_id = "intent.qa.generic"
        else:
            rule_id = "intent.qa.judgment" if judgment_qa and not domain_qa else "intent.qa.domain"
        matched_rules.append(_rule(rule_id, "qa", "medium", text))
    if chat:
        _append_signal(intent_signals, "chat")
        matched_rules.append(_rule("intent.chat.greeting", "chat", "high", text))
    if ask_capability:
        _append_signal(intent_signals, "system")
        _append_signal(intent_signals, "ask_capability")
        matched_rules.append(_rule("system.capability.ask", "ask_capability", "high", text))
    if ask_source:
        _append_signal(intent_signals, "ask_source")
        _append_signal(context_signals, "ask_source")
        matched_rules.append(_rule("source.ask_basis", "ask_source", "high", text))
    if challenge_requested:
        if ctx.has_previous_answer:
            _append_signal(intent_signals, "challenge" if hard_challenge_requested else "soft_doubt")
            _append_signal(context_signals, "challenge" if hard_challenge_requested else "soft_doubt")
            dependency_signals["previous_answer"] = True
            if hard_challenge_requested:
                matched_rules.append(_rule("challenge.disagree", "challenge", "high", text))
            else:
                matched_rules.append(_rule("challenge.soft_doubt", "soft_doubt", "low", text))
        elif _should_rescue_self_contained_long_query(text):
            _append_signal(intent_signals, "qa")
            matched_rules.append(_rule("intent.qa.long_context_rescue", "qa", "medium", text))
        else:
            _append_signal(context_signals, "needs_clarification")
            dependency_signals["ambiguous"] = True
            matched_rules.append(_rule("challenge.missing_context", "needs_clarification", "medium", text))
    if follow_up_requested and ctx.has_history:
        _append_signal(context_signals, "follow_up")
        dependency_signals["history_reference"] = True
        matched_rules.append(_rule("context.follow_up.reference", "follow_up", "medium", text))
    elif follow_up_requested and not _should_block_missing_history(text):
        _append_signal(context_signals, "needs_clarification")
        dependency_signals["ambiguous"] = True
        matched_rules.append(_rule("context.follow_up.missing_history", "needs_clarification", "medium", text))

    for rule_id, pattern, unsupported_key in UNSUPPORTED_RULES:
        match = pattern.search(text)
        if match:
            unsupported_signals[unsupported_key] = True
            _append_signal(safety_signals, "unsupported")
            _append_signal(safety_signals, "out_of_scope")
            matched_rules.append(_rule(rule_id, "out_of_scope", "high", match.group(0)))

    if multi_question:
        _append_signal(task_signals, "multi_question")
        matched_rules.append(_rule("task.enumerated_questions", "multi_question", "high", text[:80]))
    if complex_task:
        _append_signal(task_signals, "complex")
        matched_rules.append(_rule("task.complex.request", "complex", "medium", text[:80]))
    if long_complex_fallback and "qa" not in intent_signals:
        _append_signal(intent_signals, "qa")
        matched_rules.append(_rule("intent.qa.long_form", "qa", "medium", text[:80]))

    if ask_source and ctx.has_previous_answer:
        dependency_signals["previous_answer"] = True
    if ask_source and not ctx.has_previous_answer and not (domain_qa or judgment_qa or generic_qa):
        _append_signal(context_signals, "needs_clarification")
        dependency_signals["ambiguous"] = True
        matched_rules.append(_rule("source.missing_context", "needs_clarification", "medium", text))

    if (
        judgment_qa
        and "needs_clarification" not in context_signals
        and not ctx.has_history
        and not long_complex_fallback
        and not multi_question
        and not complex_task
        and _should_request_judgment_clarification(text)
    ):
        _append_signal(context_signals, "needs_clarification")
        dependency_signals["ambiguous"] = True
        matched_rules.append(_rule("intent.qa.judgment_clarify", "needs_clarification", "medium", text))

    if not any(dependency_signals.values()):
        dependency_signals["none"] = True

    typed_context_signals = ContextSignals(
        has_reference=dependency_signals["history_reference"],
        has_previous_intent=ctx.last_main_intent is not None,
        has_implicit_history=dependency_signals["ambiguous"],
        is_direct_followup="follow_up" in context_signals,
        previous_answer=dependency_signals["previous_answer"],
        previous_retrieval=dependency_signals["previous_retrieval"],
        ambiguous=dependency_signals["ambiguous"],
        none=dependency_signals["none"],
    )
    signal_buckets = SignalBuckets(
        intent=tuple(intent_signals),
        task=tuple(task_signals),
        context=tuple(context_signals),
        safety=tuple(safety_signals),
    )
    raw_signals = signal_buckets.all_signals()

    candidate_intents = _build_rule_candidate_intents(
        signal_buckets=signal_buckets,
        domain_qa=domain_qa or judgment_qa or generic_qa,
        chat=chat,
        ask_capability=ask_capability,
        unsupported=any(unsupported_signals.values()),
        multi_question=multi_question,
        complex_task=complex_task,
        long_complex_fallback=long_complex_fallback,
    )
    task_candidates = _build_task_candidates(
        text=text,
        multi_question=multi_question,
        complex_task=complex_task,
        long_complex_fallback=long_complex_fallback,
    )
    classifier_mode = _determine_classifier_mode(matched_rules)
    rule_confidence = calculate_rule_confidence(
        matched_rules=tuple(matched_rules),
        raw_signals=raw_signals,
        context_state=ctx,
        dependency_signals=dependency_signals,
    )

    return IntentEvidence(
        classifier_mode=classifier_mode,
        matched_rules=tuple(matched_rules),
        raw_signals=raw_signals,
        signal_buckets=signal_buckets,
        unsupported_signals=unsupported_signals,
        dependency_signals=dependency_signals,
        context_signals=typed_context_signals,
        candidate_intents=tuple(candidate_intents),
        task_candidates=tuple(task_candidates),
        model_result=None,
        rule_confidence=rule_confidence,
    )


def _build_rule_candidate_intents(
    *,
    signal_buckets: SignalBuckets,
    domain_qa: bool,
    chat: bool,
    ask_capability: bool,
    unsupported: bool,
    multi_question: bool,
    complex_task: bool,
    long_complex_fallback: bool,
) -> list[CandidateIntent]:
    intent_signals = set(signal_buckets.intent)
    context_signals = set(signal_buckets.context)
    if unsupported:
        return [CandidateIntent(intent="unsupported", score=0.95)]
    if ask_capability:
        return [CandidateIntent(intent="system", score=0.95)]
    if (
        "challenge" in intent_signals
        or "ask_source" in intent_signals
        or "soft_doubt" in intent_signals
        or "follow_up" in context_signals
        or domain_qa
        or complex_task
        or long_complex_fallback
    ):
        return [CandidateIntent(intent="qa", score=0.85)]
    if multi_question and "chat" not in intent_signals:
        return [CandidateIntent(intent="qa", score=0.75), CandidateIntent(intent="chat", score=0.25)]
    if chat:
        return [CandidateIntent(intent="chat", score=0.9)]
    return [CandidateIntent(intent="chat", score=0.55), CandidateIntent(intent="qa", score=0.45)]


def _build_task_candidates(
    *,
    text: str,
    multi_question: bool,
    complex_task: bool,
    long_complex_fallback: bool,
) -> list[TaskCandidate]:
    candidates: list[TaskCandidate] = []
    if multi_question:
        candidates.append(TaskCandidate(complexity="compound", shape="multi_question", score=0.9))
    if complex_task:
        shape = _infer_complex_shape(text)
        candidates.append(TaskCandidate(complexity="complex", shape=shape, score=0.8))
    elif long_complex_fallback:
        shape = _infer_complex_shape(text)
        candidates.append(TaskCandidate(complexity="complex", shape=("summarize" if shape == "mixed" else shape), score=0.7))
    if not candidates:
        candidates.append(TaskCandidate(complexity="simple", shape="single_question", score=0.8))
    return candidates


def _determine_classifier_mode(matched_rules: list[RuleMatch]) -> ClassifierMode:
    if any(match.strength == "high" and match.signal in {"out_of_scope", "ask_capability", "challenge"} for match in matched_rules):
        return "rule_only"
    if matched_rules:
        return "rule_plus_model"
    return "model_first_with_rule_guard"


def _infer_complex_shape(text: str) -> str:
    compare_score = _shape_signal_score(
        text,
        (
            r"对比|比较|差异|异同|横向(?:对比|比较)|区别在于|优劣|取舍|平衡点|选(?:哪一个|哪种)|相比",
        ),
    )
    summarize_score = _shape_signal_score(
        text,
        (
            r"总结|归纳|提炼|整理|梳理|清单|脉络|要点|全集|所有情形|分门别类|框架|逻辑线|关键事实|争议点",
        ),
    )
    extract_score = _shape_signal_score(
        text,
        (
            r"提取|抽取|摘出|列出|找出",
        ),
    )
    verify_score = _shape_signal_score(
        text,
        (
            r"验证|核对|判断对错|逐条分析|举证责任|因果关系|司法解释|是否(?:成立|支持|违背|冲突|一致)|法律效力|定性|逻辑(?:是否)?自洽|能不能认定|是否合法|责任|赔偿|连带责任",
        ),
    )

    if summarize_score and (verify_score or compare_score) and (
        len(text) >= 80 or re.search(r"请按步骤|结构化|关键事实|争议点|判断依据", text, re.IGNORECASE)
    ):
        return "mixed"

    scores = {
        "compare": compare_score,
        "summarize": summarize_score,
        "extract": extract_score,
        "verify": verify_score,
    }
    shape, score = max(scores.items(), key=lambda item: item[1])
    if score <= 0:
        return "mixed"
    return shape


def _looks_like_judgment_qa(text: str) -> bool:
    if not (_matches(text, JUDGMENT_QA_PATTERNS) or text.startswith(("这算", "这样算", "这种情况算"))):
        return False
    return bool(
        re.search(r"(医院|医生|公司|老板|物业|学校|法院|平台|商家|患者|员工|这样|这种做法|这件事|这情况)", text)
        or _contains_domain_hint(text)
        or _contains_self_anchor(text)
    )


def _looks_like_generic_qa(text: str) -> bool:
    generic_tokens = (
        "怎么办",
        "怎么处理",
        "怎么解决",
        "如何申请",
        "如何办理",
        "如何认定",
        "如何处理",
        "如何解决",
        "有哪些要求",
        "有哪些条件",
        "有哪些风险",
        "有哪些责任",
        "能不能",
        "要赔吗",
        "有责任吗",
        "合法吗",
        "违法吗",
        "有效吗",
        "对吗",
        "有问题吗",
        "区别是什么",
        "最长多少天",
        "承担哪些法律责任",
    )
    if any(token in text for token in generic_tokens) or _matches(text, META_ANALYSIS_QA_PATTERNS):
        return True
    return bool(
        (_contains_domain_hint(text) or _contains_self_anchor(text))
        and _question_phrase_count(text) >= 1
    )


def _looks_like_soft_challenge(text: str) -> bool:
    return bool(
        re.search(
            r"(真的吗|确定吗|是吗|未必|不一定|不见得|两说|太绝对|太武断|站不住|我看未必)",
            text,
            re.IGNORECASE,
        )
    )


def _contains_domain_hint(text: str) -> bool:
    return any(token in text for token in DOMAIN_HINT_TOKENS)


def _contains_self_anchor(text: str) -> bool:
    return any(token in text for token in SELF_ANCHOR_TOKENS)


def _should_block_missing_history(text: str) -> bool:
    return bool(
        re.search(
            r"(定义|算不算|医疗事故|医疗过失|因果关系|举证责任|司法解释|是什么|怎么认定|怎么处理|有责任吗|赔多少|合法吗|违法吗)",
            text,
            re.IGNORECASE,
        )
    ) or (len(text) >= 80 and (_contains_domain_hint(text) or _question_phrase_count(text) >= 2))


def _should_request_judgment_clarification(text: str) -> bool:
    if len(text) >= 30:
        return False
    if _contains_self_anchor(text):
        return False
    if re.search(r"^(这样|这算|这种|这件事|这个情况|我这种情况|这种情况)", text, re.IGNORECASE):
        return True
    return not bool(
        re.search(
            r"(医疗事故|医疗过失|法律效力|免责条款|电子合同|重大疾病|公司破产|员工工资|著作权|刑事拘留|行政拘留|侵权责任|违约责任)",
            text,
            re.IGNORECASE,
        )
    )


def _should_force_complex_qa(text: str, has_qa_signal: bool) -> bool:
    if not has_qa_signal or len(text) < 80:
        return False
    return bool(
        re.search(
            r"(举证责任|司法解释|争议点|判断依据|因果关系|请按步骤|结构化|分别说明|第一|第二|第三|另外|同时|是否合法|是否成立|是否支持|是否一致|法律效力|定性|连带责任|主张什么权利|关键事实)",
            text,
            re.IGNORECASE,
        )
        or _question_phrase_count(text) >= 2
        or text.count("？") + text.count("?") >= 2
    )


def _should_rescue_self_contained_long_query(text: str) -> bool:
    return len(text) >= 80 and (
        _contains_domain_hint(text)
        or _question_phrase_count(text) >= 2
        or _infer_complex_shape(text) in {"verify", "compare", "mixed", "summarize"}
    )


def _shape_signal_score(text: str, patterns: tuple[str, ...]) -> int:
    score = 0
    tail = _tail_slice(text)
    for pattern in patterns:
        if re.search(pattern, text, re.IGNORECASE):
            score += 1
        if tail and re.search(pattern, tail, re.IGNORECASE):
            score += 1
    return score


def _tail_slice(text: str) -> str:
    if len(text) < 150:
        return ""
    return text[int(len(text) * 0.8) :]


def _rule(rule_id: str, signal: str, strength: str, matched_text: str) -> RuleMatch:
    return RuleMatch(
        rule_id=rule_id,
        signal=signal,
        strength=strength,
        score=RULE_STRENGTH_SCORES[strength],
        matched_text=matched_text,
    )


def _append_signal(bucket: list[str], signal: str) -> None:
    if signal not in bucket:
        bucket.append(signal)


def _normalize(message: str) -> str:
    return re.sub(r"\s+", " ", str(message or "")).strip()


def _matches(text: str, patterns: tuple[Pattern[str], ...]) -> bool:
    return any(pattern.search(text) for pattern in patterns)


def _is_multi_question(text: str) -> bool:
    if _matches(text, MULTI_QUESTION_PATTERNS):
        return True
    if _question_phrase_count(text) >= 2:
        return True
    question_count = text.count("?") + text.count("？")
    return question_count >= 2


def _question_phrase_count(text: str) -> int:
    pattern = r"(最长多少天|算不算|合理吗|是否|哪些|多少|多大|怎么|如何|什么|谁|哪|几|吗)"
    return len(re.findall(pattern, text, re.IGNORECASE))


def _looks_like_design_review_query(text: str) -> bool:
    return bool(
        re.search(r"^\s*1\.", text)
        and re.search(r"(如何|为什么|评估|设计|收敛|每一层|走一遍)", text, re.IGNORECASE)
    )


def _history_last_main_intent(history: list[dict[str, Any]]) -> str | None:
    recent = history[-6:]
    for item in reversed(recent):
        content = str(item.get("content", ""))
        if _matches(content, DOMAIN_QA_PATTERNS) or item.get("retrieval_steps"):
            return "qa"
    return None
