from __future__ import annotations

import re
from collections import Counter

from knowledge_retrieval.types import Evidence


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[\u4e00-\u9fff]|[A-Za-z0-9_]+", text.lower())


class HeuristicCrossEncoderReranker:
    """可替换的精排器。

    当前仓库没有稳定可调用的 cross-encoder 模型，因此先用
    query/snippet/source path 的联合匹配做 deterministic rerank。
    后续只需要替换 `score()` 即可接真实 cross-encoder。
    """

    def rerank(self, query: str, evidences: list[Evidence], *, top_k: int) -> list[Evidence]:
        scored = [(self.score(query, item), item) for item in evidences]
        scored.sort(key=lambda item: item[0], reverse=True)
        output: list[Evidence] = []
        for score, evidence in scored[:top_k]:
            evidence.score = max(score, evidence.score or 0.0)
            output.append(evidence)
        return output

    def score(self, query: str, evidence: Evidence) -> float:
        query_terms = Counter(_tokenize(query))
        snippet_terms = Counter(_tokenize(evidence.snippet))
        path_terms = Counter(_tokenize(evidence.source_path))
        if not query_terms:
            return evidence.score or 0.0
        overlap = sum(min(count, snippet_terms.get(term, 0)) for term, count in query_terms.items())
        path_overlap = sum(min(count, path_terms.get(term, 0)) for term, count in query_terms.items())
        exact_phrase = 1.0 if re.sub(r"\s+", "", query.lower()) in re.sub(r"\s+", "", evidence.snippet.lower()) else 0.0
        base = (evidence.score or 0.0) * 0.55
        lexical = overlap / max(1, sum(query_terms.values()))
        return round(base + lexical * 0.3 + (path_overlap / max(1, sum(query_terms.values()))) * 0.1 + exact_phrase * 0.05, 6)
