from __future__ import annotations

import json
import re
from typing import Any


class KnowledgeQueryRewriteHelper:
    """为知识检索补一个轻量 bilingual rewrite，提升中问英料的召回率。"""

    _JSON_BLOCK = re.compile(r"\{.*\}", re.DOTALL)
    _CJK = re.compile(r"[\u3400-\u9fff]")

    def rewrite(
        self,
        query: str,
        *,
        llm_call: Any | None,
    ) -> dict[str, Any]:
        normalized_query = str(query).strip()
        if not normalized_query or llm_call is None or not self._should_rewrite(normalized_query):
            return {
                "applied": False,
                "query": normalized_query,
                "rewritten_query": None,
                "query_hints": (),
            }

        prompt = self._build_prompt(normalized_query)
        try:
            raw_payload = str(llm_call(prompt) or "").strip()
            payload = self._parse_payload(raw_payload)
        except Exception:
            return {
                "applied": False,
                "query": normalized_query,
                "rewritten_query": None,
                "query_hints": (),
            }

        rewritten_query = str(payload.get("rewritten_query") or "").strip()
        query_hints = self._normalize_hints(payload.get("query_hints"))
        merged_query = self._merge_query(normalized_query, rewritten_query, query_hints)
        return {
            "applied": merged_query != normalized_query,
            "query": merged_query,
            "rewritten_query": rewritten_query or None,
            "query_hints": query_hints,
        }

    def _should_rewrite(self, query: str) -> bool:
        return bool(self._CJK.search(query))

    def _build_prompt(self, query: str) -> str:
        return (
            "你是知识检索 query rewrite 助手。\n"
            "任务：把用户的中文知识查询改写成更适合检索中英文资料的 query。\n"
            "要求：\n"
            "1. 保留原问题意图，不要回答问题。\n"
            "2. 输出 bilingual 检索词，尤其补充英文术语、别名、缩写、论文题名关键词。\n"
            "3. 不要虚构文献，不要补和问题无关的方向。\n"
            "4. 只输出 JSON。\n"
            'JSON schema: {"rewritten_query": "string", "query_hints": ["string"]}\n'
            f"用户问题：{query}"
        )

    def _parse_payload(self, payload: str) -> dict[str, Any]:
        if not payload:
            return {}
        match = self._JSON_BLOCK.search(payload)
        candidate = match.group(0) if match else payload
        data = json.loads(candidate)
        return data if isinstance(data, dict) else {}

    def _normalize_hints(self, hints: object) -> tuple[str, ...]:
        if not isinstance(hints, (list, tuple)):
            return ()
        normalized: list[str] = []
        seen: set[str] = set()
        for item in hints:
            hint = str(item or "").strip()
            if not hint:
                continue
            lowered = hint.lower()
            if lowered in seen:
                continue
            seen.add(lowered)
            normalized.append(hint[:120])
            if len(normalized) >= 6:
                break
        return tuple(normalized)

    def _merge_query(
        self,
        query: str,
        rewritten_query: str,
        query_hints: tuple[str, ...],
    ) -> str:
        parts: list[str] = [query]
        seen = {query.lower()}
        for item in (rewritten_query, *query_hints):
            text = str(item or "").strip()
            if not text:
                continue
            lowered = text.lower()
            if lowered in seen:
                continue
            seen.add(lowered)
            parts.append(text)
        merged = " ".join(parts).strip()
        return merged[:600]
