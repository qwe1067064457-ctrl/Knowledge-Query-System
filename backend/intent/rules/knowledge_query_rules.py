from __future__ import annotations

import re

KNOWLEDGE_QUERY_PATTERNS = (
    re.compile(r"知识库"),
    re.compile(r"\bknowledge\b", re.IGNORECASE),
    re.compile(r"根据.+?(知识库|文档|资料)"),
    re.compile(r"(查|检索).+?(文档|资料|报告|白皮书)"),
    re.compile(r"\.(pdf|xlsx|xls|json)\b", re.IGNORECASE),
    re.compile(r"\b(doi|pmid|arxiv)\b", re.IGNORECASE),
    re.compile(r"(论文|文献|研究|期刊).{0,20}(突破|价值|结论|结果|发现|方法)"),
    re.compile(r"(发表于|发表在).{0,30}(science|nature|cell|lancet|jama|nejm)", re.IGNORECASE),
    re.compile(r"\b(science advances|nature communications|journal|article)\b", re.IGNORECASE),
    re.compile(r"(相对于|相比).{0,20}(传统|现有).{0,20}(方法|连接法|方案)"),
)


def is_knowledge_query(message: str) -> bool:
    return any(pattern.search(message) for pattern in KNOWLEDGE_QUERY_PATTERNS)
