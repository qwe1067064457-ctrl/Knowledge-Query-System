from __future__ import annotations

import re

KNOWLEDGE_QUERY_PATTERNS = (
    re.compile(r"知识库"),
    re.compile(r"\bknowledge\b", re.IGNORECASE),
    re.compile(r"根据.+?(知识库|文档|资料)"),
    re.compile(r"(查|检索).+?(文档|资料|报告|白皮书)"),
    re.compile(r"\.(pdf|xlsx|xls|json)\b", re.IGNORECASE),
)


def is_knowledge_query(message: str) -> bool:
    return any(pattern.search(message) for pattern in KNOWLEDGE_QUERY_PATTERNS)
