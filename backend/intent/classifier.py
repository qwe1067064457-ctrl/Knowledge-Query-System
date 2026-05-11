from __future__ import annotations

import re
from typing import Any, Iterable, Pattern

from intent.control_signal import build_control_signal
from intent.resolver import resolve_intent
from intent.types import (
    CandidateIntent,
    ClassifierMode,
    ContextState,
    IntentAnalysis,
    IntentEvidence,
    IntentInput,
    IntentModifiers,
    ModelContext,
    RuleMatch,
    TaskCandidate,
)


RULE_STRENGTH_SCORES = {"high": 0.9, "medium": 0.6, "low": 0.3}

DOMAIN_QA_PATTERNS: tuple[Pattern[str], ...] = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"知识库|文档|资料|制度|流程|报告|政策",
        r"法律|法规|法条|条款|合同|劳动|试用期|赔偿|仲裁|诉讼|法院|判决",
        r"医学|病例|诊断|药品|治疗|检查|指南",
        r"根据.+?(规定|资料|知识库|文档|法律|制度)",
        r"(查|检索|引用|总结|对比|提取|整理|分析).+?(资料|文档|知识库|文件|报告|制度)",
    )
)
CHALLENGE_PATTERNS: tuple[Pattern[str], ...] = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"你确定吗|确定吗|真的吗|靠谱么|靠谱吗",
        r"不对吧|不正确|错了|错误|有问题|不严谨",
        r"是不是.+?(错|不对|有问题)",
        r"你刚才.+?(不对|错|矛盾|不一致)",
        r"和.+?(不一致|矛盾|冲突)",
    )
)
ASK_SOURCE_PATTERNS: tuple[Pattern[str], ...] = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"依据是什么|依据呢|什么依据",
        r"来源|出处|引用|证据",
        r"哪一条|哪条|哪个文件|哪份资料",
        r"\b(source|citation|reference)\b",
    )
)
CAPABILITY_PATTERNS: tuple[Pattern[str], ...] = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"你能做什么|你可以做什么|能干什么",
        r"有什么功能|支持什么|怎么用",
        r"你是谁|介绍一下你自己",
    )
)
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
FOLLOW_UP_PATTERNS: tuple[Pattern[str], ...] = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"^(那|那么|如果|要是|这种|这个|上述|刚才|前面)",
        r"(这种情况|这个情况|那种情况|上述情况|刚才说的|前面说的)",
        r"^(继续|还有吗|还有呢|再说|展开说)",
        r"(它|这个|那个|上述|前者|后者).{0,8}(呢|吗|如何|怎么|是否|多久|多少)",
    )
)
CHAT_PATTERNS: tuple[Pattern[str], ...] = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"^(你好|您好|嗨|hello|hi)[！!。,.，\s]*$",
        r"^(谢谢|感谢|辛苦了|好的|明白了)[！!。,.，\s]*$",
    )
)
MULTI_QUESTION_PATTERNS: tuple[Pattern[str], ...] = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"\?.+\?",
        r"？.+？",
        r"^\s*1\.",
        r"[；;].+[？?]",
    )
)
COMPLEX_TASK_PATTERNS: tuple[Pattern[str], ...] = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"对比|比较|差异|异同",
        r"总结|归纳|提炼|整理",
        r"验证|核对|判断对错|逐条分析",
        r"表格|清单|分步骤|逐层|结构化",
        r"如何收敛|合理性评估|每一层|走一遍|设计说明",
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
    raw_signals: list[str] = []
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
    challenge_requested = _matches(text, CHALLENGE_PATTERNS)
    follow_up_requested = _matches(text, FOLLOW_UP_PATTERNS)
    multi_question = _is_multi_question(text)
    complex_task = _matches(text, COMPLEX_TASK_PATTERNS) or _looks_like_design_review_query(text)

    if domain_qa:
        raw_signals.append("qa")
        matched_rules.append(_rule("intent.qa.domain", "qa", "medium", text))
    if chat:
        raw_signals.append("chat")
        matched_rules.append(_rule("intent.chat.greeting", "chat", "high", text))
    if ask_capability:
        raw_signals.extend(["system", "ask_capability"])
        matched_rules.append(_rule("system.capability.ask", "ask_capability", "high", text))
    if ask_source:
        raw_signals.append("ask_source")
        matched_rules.append(_rule("source.ask_basis", "ask_source", "high", text))
    if challenge_requested:
        if ctx.has_previous_answer:
            raw_signals.append("challenge")
            dependency_signals["previous_answer"] = True
            matched_rules.append(_rule("challenge.disagree", "challenge", "high", text))
        else:
            raw_signals.append("needs_clarification")
            dependency_signals["ambiguous"] = True
            matched_rules.append(_rule("challenge.missing_context", "needs_clarification", "medium", text))
    if follow_up_requested and ctx.has_history:
        raw_signals.append("follow_up")
        dependency_signals["history_reference"] = True
        matched_rules.append(_rule("context.follow_up.reference", "follow_up", "medium", text))
    elif follow_up_requested:
        raw_signals.append("needs_clarification")
        dependency_signals["ambiguous"] = True
        matched_rules.append(_rule("context.follow_up.missing_history", "needs_clarification", "medium", text))

    for rule_id, pattern, unsupported_key in UNSUPPORTED_RULES:
        match = pattern.search(text)
        if match:
            unsupported_signals[unsupported_key] = True
            raw_signals.extend(["unsupported", "out_of_scope"])
            matched_rules.append(_rule(rule_id, "out_of_scope", "high", match.group(0)))

    if multi_question:
        raw_signals.append("multi_question")
        matched_rules.append(_rule("task.enumerated_questions", "multi_question", "high", text[:80]))
    if complex_task:
        raw_signals.append("complex")
        matched_rules.append(_rule("task.complex.request", "complex", "medium", text[:80]))

    if ask_source and ctx.has_previous_answer:
        dependency_signals["previous_answer"] = True
    if ask_source and not ctx.has_previous_answer and not domain_qa:
        raw_signals.append("needs_clarification")
        dependency_signals["ambiguous"] = True
        matched_rules.append(_rule("source.missing_context", "needs_clarification", "medium", text))

    if not any(dependency_signals.values()):
        dependency_signals["none"] = True

    candidate_intents = _build_rule_candidate_intents(
        raw_signals=raw_signals,
        domain_qa=domain_qa,
        chat=chat,
        ask_capability=ask_capability,
        unsupported=any(unsupported_signals.values()),
    )
    task_candidates = _build_task_candidates(
        text=text,
        multi_question=multi_question,
        complex_task=complex_task,
    )
    classifier_mode = _determine_classifier_mode(matched_rules)

    return IntentEvidence(
        classifier_mode=classifier_mode,
        matched_rules=tuple(matched_rules),
        raw_signals=tuple(dict.fromkeys(raw_signals)),
        unsupported_signals=unsupported_signals,
        dependency_signals=dependency_signals,
        candidate_intents=tuple(candidate_intents),
        task_candidates=tuple(task_candidates),
        model_result=None,
    )


def _build_rule_candidate_intents(
    *,
    raw_signals: list[str],
    domain_qa: bool,
    chat: bool,
    ask_capability: bool,
    unsupported: bool,
) -> list[CandidateIntent]:
    if unsupported:
        return [CandidateIntent(intent="unsupported", score=0.95)]
    if ask_capability:
        return [CandidateIntent(intent="system", score=0.95)]
    if "challenge" in raw_signals or "ask_source" in raw_signals or domain_qa:
        return [CandidateIntent(intent="qa", score=0.85)]
    if chat:
        return [CandidateIntent(intent="chat", score=0.9)]
    return [CandidateIntent(intent="chat", score=0.55), CandidateIntent(intent="qa", score=0.45)]


def _build_task_candidates(
    *,
    text: str,
    multi_question: bool,
    complex_task: bool,
) -> list[TaskCandidate]:
    candidates: list[TaskCandidate] = []
    if multi_question:
        candidates.append(TaskCandidate(complexity="compound", shape="multi_question", score=0.9))
    if complex_task:
        shape = _infer_complex_shape(text)
        candidates.append(TaskCandidate(complexity="complex", shape=shape, score=0.8))
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
    if re.search(r"对比|比较|差异|异同", text, re.IGNORECASE):
        return "compare"
    if re.search(r"总结|归纳|提炼|整理", text, re.IGNORECASE):
        return "summarize"
    if re.search(r"提取|抽取|摘出", text, re.IGNORECASE):
        return "extract"
    if re.search(r"验证|核对|判断对错|逐条分析", text, re.IGNORECASE):
        return "verify"
    return "mixed"


def _rule(rule_id: str, signal: str, strength: str, matched_text: str) -> RuleMatch:
    return RuleMatch(
        rule_id=rule_id,
        signal=signal,
        strength=strength,
        score=RULE_STRENGTH_SCORES[strength],
        matched_text=matched_text,
    )


def _normalize(message: str) -> str:
    return re.sub(r"\s+", " ", str(message or "")).strip()


def _matches(text: str, patterns: tuple[Pattern[str], ...]) -> bool:
    return any(pattern.search(text) for pattern in patterns)


def _is_multi_question(text: str) -> bool:
    if _matches(text, MULTI_QUESTION_PATTERNS):
        return True
    question_count = text.count("?") + text.count("？")
    return question_count >= 2


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
