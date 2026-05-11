from __future__ import annotations

import re
from typing import Any, Iterable, Pattern

from intent.types import IntentModifiers, IntentResult


DOMAIN_QA_PATTERNS: tuple[Pattern[str], ...] = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"知识库|文档|资料|制度|流程|报告|政策",
        r"法律|法规|法条|条款|合同|劳动|试用期|赔偿|仲裁|诉讼|法院|判决",
        r"医学|病例|诊断|药品|治疗|检查|指南",
        r"根据.+?(规定|资料|知识库|文档|法律|制度)",
        r"(查|检索|引用|总结|对比|提取).+?(资料|文档|知识库|文件|报告|制度)",
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

OUT_OF_SCOPE_PATTERNS: tuple[Pattern[str], ...] = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"(删除|移除|清空|覆盖|重命名|上传|导入|新建|新增|创建|修改|更新).{0,12}(文件|文档|资料|知识库|目录|数据|记录)",
        r"(文件|文档|资料|知识库|目录|数据|记录).{0,12}(删除|移除|清空|覆盖|重命名|上传|导入|新建|新增|创建|修改|更新)",
    )
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


def classify_intent(
    message: str,
    history: Iterable[dict[str, Any]] | None = None,
) -> IntentResult:
    text = _normalize(message)
    history_items = list(history or [])
    has_assistant_history = _has_assistant_message(history_items)
    history_suggests_qa = _history_suggests_qa(history_items)

    ask_capability = _matches(text, CAPABILITY_PATTERNS)
    out_of_scope = _matches(text, OUT_OF_SCOPE_PATTERNS)
    ask_source = _matches(text, ASK_SOURCE_PATTERNS)
    challenge_requested = _matches(text, CHALLENGE_PATTERNS)
    challenge = challenge_requested and has_assistant_history
    domain_qa = _matches(text, DOMAIN_QA_PATTERNS)
    chat = _matches(text, CHAT_PATTERNS)

    follow_up = _is_follow_up(
        text,
        has_history=bool(history_items),
        is_meta=challenge or ask_source,
    )

    needs_clarification = False
    if challenge_requested and not has_assistant_history:
        needs_clarification = True
    elif ask_source and not has_assistant_history and not domain_qa:
        needs_clarification = True
    elif not history_items and _looks_like_context_dependent_question(text) and not domain_qa:
        needs_clarification = True

    if out_of_scope or ask_capability or chat:
        main_intent = "chat"
    elif challenge or (ask_source and has_assistant_history):
        main_intent = "qa"
    elif domain_qa:
        main_intent = "qa"
    elif follow_up and history_suggests_qa:
        main_intent = "qa"
    else:
        main_intent = "chat"

    matched = _matched_signals(
        follow_up=follow_up,
        challenge=challenge,
        ask_source=ask_source,
        ask_capability=ask_capability,
        needs_clarification=needs_clarification,
        out_of_scope=out_of_scope,
        domain_qa=domain_qa,
    )
    return IntentResult(
        main_intent=main_intent,
        modifiers=IntentModifiers(
            follow_up=follow_up,
            challenge=challenge,
            ask_source=ask_source,
            ask_capability=ask_capability,
            needs_clarification=needs_clarification,
            out_of_scope=out_of_scope,
        ),
        matched_signals=matched,
    )


def _normalize(message: str) -> str:
    return re.sub(r"\s+", " ", str(message or "")).strip()


def _matches(text: str, patterns: tuple[Pattern[str], ...]) -> bool:
    return any(pattern.search(text) for pattern in patterns)


def _has_assistant_message(history: list[dict[str, Any]]) -> bool:
    return any(
        item.get("role") == "assistant" and str(item.get("content", "")).strip()
        for item in history
    )


def _history_suggests_qa(history: list[dict[str, Any]]) -> bool:
    recent = history[-6:]
    for item in recent:
        content = str(item.get("content", ""))
        if _matches(content, DOMAIN_QA_PATTERNS):
            return True
        if item.get("retrieval_steps"):
            return True
    return False


def _is_follow_up(text: str, *, has_history: bool, is_meta: bool) -> bool:
    if not has_history:
        return False
    if _matches(text, CHAT_PATTERNS) or _matches(text, CAPABILITY_PATTERNS):
        return False
    if is_meta:
        return True
    return _matches(text, FOLLOW_UP_PATTERNS)


def _looks_like_context_dependent_question(text: str) -> bool:
    return _matches(text, FOLLOW_UP_PATTERNS) or bool(re.search(r"^(那|这个|这种|它).{0,20}[?？]?$", text))


def _matched_signals(**signals: bool) -> tuple[str, ...]:
    return tuple(name for name, enabled in signals.items() if enabled)
