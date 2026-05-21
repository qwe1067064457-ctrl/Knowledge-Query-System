from __future__ import annotations

import re
from typing import Pattern


MULTI_QUESTION_PATTERNS: tuple[Pattern[str], ...] = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"\?.+\?",
        r"？.+？",
        r"^\s*1\.",
        r"(第一|第二|第三|首先|其次)",
    )
)

PARALLEL_SUBTASK_PATTERNS: tuple[Pattern[str], ...] = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"分别(?:说明|列出|给出|整理|分析)",
        r"(方面|维度|角度).{0,20}(说明|分析|展开)",
        r"(逐条|逐项)(?:说明|列出|分析)",
    )
)

STAGED_TASK_PATTERNS: tuple[Pattern[str], ...] = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"先判断.+再说.+最后",
        r"按步骤|分步骤|一步一步|逐步",
        r"先核验.{0,20}再",
    )
)

GENERIC_QA_PATTERNS: tuple[Pattern[str], ...] = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"(怎么|如何).{0,12}(办|处理|解决|申请|计算|确定|认定)",
        r"有哪些.{0,4}(要求|条件|风险|责任)",
        r"能不能|有问题吗|对吗|区别是什么|最长多少天",
        r"会有什么后果|有什么后果|后果是什么",
        r"承担哪些法律责任|应该考虑哪些因素",
    )
)

COMPLEX_TASK_PATTERNS: tuple[Pattern[str], ...] = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"对比|比较|差异|异同",
        r"总结|归纳|提炼|整理|清单",
        r"验证|核对|判断对错|逐条分析|举证责任|因果关系",
        r"表格|结构化|决策树|分析框架",
        r"关键事实|争议点|判断依据",
    )
)
