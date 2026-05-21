from __future__ import annotations

import re
from typing import Pattern


def _compile_patterns(patterns: tuple[str, ...]) -> tuple[Pattern[str], ...]:
    return tuple(re.compile(pattern, re.IGNORECASE) for pattern in patterns)


FOLLOW_UP_PATTERNS = _compile_patterns(
    (
        r"^(那如果|那么|如果|这个|这种|上述|刚才|前面)",
        r"^(继续|再说|展开说)",
        r"(这个|那个|这种|前面).{0,8}(怎么|如何|是否|多久|多少)",
    )
)


ANSWER_STRUCTURE_PATTERNS = _compile_patterns(
    (
        r"先说.{0,20}再说.{0,20}再说",
        r"(是否成立|依据|风险|结论|争议点|建议)",
    )
)


def looks_like_answer_structure_request(text: str) -> bool:
    return bool(
        ANSWER_STRUCTURE_PATTERNS[0].search(text)
        and ANSWER_STRUCTURE_PATTERNS[1].search(text)
    )
