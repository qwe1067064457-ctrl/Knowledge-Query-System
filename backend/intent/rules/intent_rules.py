from __future__ import annotations

import re
from typing import Pattern


def _compile_patterns(patterns: tuple[str, ...]) -> tuple[Pattern[str], ...]:
    return tuple(re.compile(pattern, re.IGNORECASE) for pattern in patterns)


ASK_SOURCE_PATTERNS = _compile_patterns(
    (
        r"依据是什么",
        r"来源|出处|引用|根据哪条|哪一条",
        r"\b(source|citation|reference)\b",
    )
)

CHALLENGE_PATTERNS = _compile_patterns(
    (
        r"你确定吗",
        r"不对|错误|矛盾|不一致",
        r"胡说|乱说",
    )
)

CAPABILITY_PATTERNS = _compile_patterns(
    (
        r"你能做什么",
        r"有什么功能|支持什么",
        r"能力范围|支持范围|介绍一下你自己",
    )
)

CHAT_PATTERNS = _compile_patterns(
    (
        r"^(你好|您好|hello|hi)[,，。!\s]*$",
        r"^(谢谢|感谢|辛苦了|好的|明白了)[,，。!\s]*$",
    )
)

META_ANALYSIS_QA_PATTERNS = _compile_patterns(
    (
        r"(代码|规则|classifier|resolver|control|query|intent|rule_id).{0,16}(判断|分流|识别|解析|收敛)",
        r"(看.{0,8}(代码|规则).{0,16}(解析|判断|分流|识别))",
        r"(当前|现在).{0,4}(规则|分类器).{0,16}(判断|识别|分流)",
    )
)
