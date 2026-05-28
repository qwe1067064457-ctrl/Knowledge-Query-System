from __future__ import annotations

import re
from typing import Any

from memory_system.session_working_memory.models import SessionWorkingMemory, WorkingMemoryEntry


class SessionWorkingMemoryResolver:
    _CHALLENGE_HINTS = ("不对", "有问题", "依据", "为什么", "漏了", "不成立", "错了")
    _FOLLOW_UP_HINTS = ("这个", "那个", "上面", "刚才", "前面", "另一个", "第二个", "前两个", "第一点", "第二点", "第三点", "第一个", "第三个")
    _MULTI_HINTS = ("分别", "前两个", "两个", "两条", "以及", "和")
    _ASSERTION_HINTS = ("这个说法", "那个说法", "这个结论", "那个结论", "你刚才说的", "你上面说的")
    _SELF_CONTAINED_COMPARISON_HINTS = ("区别", "不同", "差异", "关系", "比较", "对比")

    def classify_query_style(self, query: str) -> str:
        if any(token in query for token in self._CHALLENGE_HINTS):
            return "challenge"
        if self._is_self_contained_comparison_query(query):
            return "standalone"
        if any(token in query for token in self._MULTI_HINTS):
            return "multi_target"
        if any(token in query for token in self._FOLLOW_UP_HINTS):
            return "follow_up"
        return "standalone"

    def _is_self_contained_comparison_query(self, query: str) -> bool:
        if "和" not in query and "以及" not in query:
            return False
        if not any(token in query for token in self._SELF_CONTAINED_COMPARISON_HINTS):
            return False
        if any(token in query for token in self._FOLLOW_UP_HINTS):
            return False
        return True

    def build_relevant_entries(
        self,
        *,
        query: str,
        working_memory: SessionWorkingMemory | dict[str, Any] | None,
        max_candidates: int = 5,
    ) -> list[WorkingMemoryEntry]:
        memory = (
            working_memory
            if isinstance(working_memory, SessionWorkingMemory)
            else SessionWorkingMemory.from_dict(working_memory)
        ) if working_memory else SessionWorkingMemory()
        entries = memory.active_entries() or memory.entries
        query_style = self.classify_query_style(query)
        filtered = self._filter_by_type(entries, query_style=query_style)
        filtered = self._apply_explicit_patterns(query, filtered)
        ranked = sorted(filtered, key=lambda entry: self._score_entry(query, entry, query_style), reverse=True)
        return ranked[:max_candidates]

    def _filter_by_type(self, entries: list[WorkingMemoryEntry], *, query_style: str) -> list[WorkingMemoryEntry]:
        allowed = {
            "challenge": {"answer_unit", "user_assertion", "review_outcome"},
            "follow_up": {"resolved_query", "answer_unit", "focus_task", "review_outcome"},
            "multi_target": {"answer_unit", "user_assertion", "resolved_query"},
            "standalone": {"resolved_query", "focus_task"},
        }.get(query_style, {"resolved_query", "focus_task"})
        result = [entry for entry in entries if entry.entry_type in allowed and entry.status == "active"]
        return result or [entry for entry in entries if entry.status == "active"]

    def _apply_explicit_patterns(self, query: str, entries: list[WorkingMemoryEntry]) -> list[WorkingMemoryEntry]:
        for token, index in {"第一个": 1, "第一点": 1, "第二个": 2, "第二点": 2, "第三个": 3, "第三点": 3}.items():
            if token in query:
                matched = [
                    entry for entry in entries
                    if entry.entry_type == "answer_unit"
                    and int(entry.structured_payload.get("unit_index", 0) or 0) == index
                ]
                if matched:
                    return matched
        if any(token in query for token in ("前两个", "两个", "两条", "分别")):
            return entries[:2]
        if any(token in query for token in self._ASSERTION_HINTS):
            prioritized = [entry for entry in entries if entry.entry_type in {"answer_unit", "user_assertion"}]
            if prioritized:
                return prioritized
        if any(token in query for token in ("这个", "那个", "上面那个", "刚才那个")):
            narrowed = [entry for entry in entries if entry.entry_type in {"answer_unit", "user_assertion", "review_outcome"}]
            if narrowed:
                return narrowed
        return entries

    def _score_entry(self, query: str, entry: WorkingMemoryEntry, query_style: str) -> int:
        score = 0
        type_bonus = {
            "focus_task": 8,
            "resolved_query": 10,
            "answer_unit": 15,
            "user_assertion": 14,
            "review_outcome": 12,
        }
        score += type_bonus.get(entry.entry_type, 0)
        if entry.confidence == "high":
            score += 10
        elif entry.confidence == "medium":
            score += 4
        for token in self._extract_keywords(query):
            if token and token in entry.content:
                score += 3
        if query_style == "challenge" and entry.entry_type in {"answer_unit", "user_assertion"}:
            score += 8
        return score

    def _extract_keywords(self, text: str) -> list[str]:
        return [token for token in re.findall(r"[\u4e00-\u9fff]{1,6}|[A-Za-z0-9_]+", text) if token.strip()]
