from __future__ import annotations

import re
from typing import Any


class BindingWorker:
    _EXPLICIT_PATTERNS = (
        re.compile(r"(这个|那个|上面那个|你刚才说的)"),
        re.compile(r"(前两个|第二种|后一种)"),
    )
    _MULTI_TARGET_PATTERNS = (
        re.compile(r"前两个"),
        re.compile(r"两个"),
        re.compile(r"两条"),
        re.compile(r"多条"),
        re.compile(r"分别"),
        re.compile(r"以及"),
        re.compile(r"和"),
        re.compile(r"、"),
        re.compile(r"这些"),
        re.compile(r"以上"),
        re.compile(r"都"),
    )
    _CHALLENGE_TOKENS = ("不对", "有问题", "依据", "为什么", "漏了", "不成立", "错了")
    _FOLLOW_UP_TOKENS = ("这个", "那个", "上面", "刚才", "前面", "另一个", "第二个", "前两个", "第一点", "第二点", "第三点", "第一个", "第三个")
    _ASSERTION_TOKENS = ("这个说法", "那个说法", "这个结论", "那个结论", "你刚才说的", "你上面说的")

    def classify_query_style(self, query: str) -> str:
        if any(token in query for token in self._CHALLENGE_TOKENS):
            return "challenge"
        if any(token in query for token in ("分别", "前两个", "两个", "两条", "以及", "和", "都")):
            return "multi_target"
        if any(token in query for token in self._FOLLOW_UP_TOKENS):
            return "follow_up"
        return "standalone"

    def filter_relevant_set(
        self,
        *,
        query: str,
        candidates: list[dict[str, Any]],
        query_style: str | None = None,
        max_candidates: int = 5,
    ) -> dict[str, Any]:
        style = query_style or self.classify_query_style(query)
        filtered = self._filter_by_type(candidates, query_style=style)
        filtered = self._apply_explicit_filters(query, filtered)
        scored = sorted(
            filtered,
            key=lambda item: self._score_candidate(query, item, query_style=style),
            reverse=True,
        )
        relevant_set = scored[:max_candidates]
        direct_resolution = self._direct_resolution(query, relevant_set)
        return {
            "query_style": style,
            "relevant_set": tuple(relevant_set),
            "direct_resolution": direct_resolution,
        }

    def select_targets(
        self,
        *,
        query: str,
        candidates: list[dict[str, Any]],
        focus_object_id: str | None = None,
    ) -> dict[str, Any]:
        if not candidates:
            return {
                "binding_ambiguous": True,
                "selected_targets": (),
                "binding_confidence": "low",
                "matched_by": "no_candidates",
                "ambiguity_reason": "no_candidates",
                "notes": ("worker_no_candidates",),
            }

        if self._should_bind_multiple(query, candidates):
            selected = tuple(candidates[: self._multi_target_limit(query, candidates)])
            return {
                "binding_ambiguous": False,
                "selected_targets": selected,
                "binding_confidence": "medium",
                "matched_by": "explicit_multi_target",
                "ambiguity_reason": None,
                "notes": ("worker_binding_multi",),
            }

        explicit_hit = any(pattern.search(query) for pattern in self._EXPLICIT_PATTERNS)
        if explicit_hit and len(candidates) == 1:
            return {
                "binding_ambiguous": False,
                "selected_targets": (candidates[0],),
                "binding_confidence": "high",
                "matched_by": "explicit_single_candidate",
                "ambiguity_reason": None,
                "notes": ("worker_binding_explicit_single",),
            }

        if explicit_hit and focus_object_id:
            for candidate in reversed(candidates):
                if str(candidate.get("object_id") or "") == str(focus_object_id):
                    return {
                        "binding_ambiguous": False,
                        "selected_targets": (candidate,),
                        "binding_confidence": "medium",
                        "matched_by": "focus_object_continuity",
                        "ambiguity_reason": None,
                        "notes": ("worker_binding_focus_object",),
                    }

        if len(candidates) == 1:
            return {
                "binding_ambiguous": False,
                "selected_targets": (candidates[0],),
                "binding_confidence": "medium",
                "matched_by": "single_candidate_fallback",
                "ambiguity_reason": None,
                "notes": ("worker_binding_single",),
            }

        return {
            "binding_ambiguous": True,
            "selected_targets": (),
            "binding_confidence": "low",
            "matched_by": "rule_ambiguous",
            "ambiguity_reason": "multiple_candidates_need_resolution",
            "notes": ("worker_binding_ambiguous",),
        }

    def bind(self, *, query: str, candidates: list[dict[str, Any]]) -> dict[str, Any]:
        selected = self.select_targets(query=query, candidates=candidates)
        return {
            "binding_ambiguous": selected["binding_ambiguous"],
            "bound_targets": selected["selected_targets"],
            "binding_confidence": selected["binding_confidence"],
            "matched_by": selected.get("matched_by"),
            "ambiguity_reason": selected.get("ambiguity_reason"),
            "notes": selected.get("notes", ()),
        }

    def _should_bind_multiple(self, query: str, candidates: list[dict[str, Any]]) -> bool:
        if len(candidates) < 2:
            return False
        return any(pattern.search(query) for pattern in self._MULTI_TARGET_PATTERNS)

    def _multi_target_limit(self, query: str, candidates: list[dict[str, Any]]) -> int:
        if "前两个" in query or "两个" in query or "两条" in query:
            return 2
        return min(len(candidates), 3)

    def _filter_by_type(self, candidates: list[dict[str, Any]], *, query_style: str) -> list[dict[str, Any]]:
        allowed = {
            "challenge": {"answer_unit", "user_assertion", "review_outcome", "question_object"},
            "follow_up": {"resolved_query", "answer_unit", "focus_task", "review_outcome", "question_object"},
            "multi_target": {"answer_unit", "user_assertion", "resolved_query", "question_object"},
            "standalone": {"resolved_query", "focus_task", "question_object"},
        }.get(query_style, {"resolved_query", "focus_task", "question_object"})
        filtered = [
            candidate
            for candidate in candidates
            if str(candidate.get("status") or "active") == "active"
            and str(candidate.get("object_type") or candidate.get("entry_type") or "question_object") in allowed
        ]
        return filtered or list(candidates)

    def _apply_explicit_filters(self, query: str, candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
        ordinal_tokens = {"第一个": 1, "第一点": 1, "第二个": 2, "第二点": 2, "第三个": 3, "第三点": 3}
        for token, index in ordinal_tokens.items():
            if token in query:
                matched = [
                    item for item in candidates
                    if int(item.get("unit_index") or item.get("structured_payload", {}).get("unit_index", 0) or 0) == index
                ]
                if matched:
                    return matched
        if any(pattern.search(query) for pattern in self._MULTI_TARGET_PATTERNS):
            return candidates[: self._multi_target_limit(query, candidates)]
        if any(token in query for token in self._ASSERTION_TOKENS):
            prioritized = [
                item for item in candidates
                if str(item.get("object_type") or item.get("entry_type") or "") in {"answer_unit", "user_assertion"}
            ]
            if prioritized:
                return prioritized
        if any(token in query for token in ("这个", "那个", "上面那个", "刚才那个")):
            narrowed = [
                item for item in candidates
                if str(item.get("object_type") or item.get("entry_type") or "") in {"answer_unit", "user_assertion", "review_outcome", "question_object"}
            ]
            if narrowed:
                return narrowed
        return candidates

    def _score_candidate(self, query: str, candidate: dict[str, Any], *, query_style: str) -> int:
        score = 0
        kind = str(candidate.get("object_type") or candidate.get("entry_type") or "question_object")
        type_bonus = {
            "focus_task": 8,
            "resolved_query": 10,
            "answer_unit": 15,
            "user_assertion": 14,
            "review_outcome": 12,
            "question_object": 10,
        }
        score += type_bonus.get(kind, 0)
        confidence = str(candidate.get("confidence") or "medium").strip().lower()
        if confidence == "high":
            score += 10
        elif confidence == "medium":
            score += 4
        content = str(candidate.get("content") or "").strip()
        for token in re.findall(r"[\u4e00-\u9fff]{1,6}|[A-Za-z0-9_]+", query):
            if token and token in content:
                score += 3
        if query_style == "challenge" and kind in {"answer_unit", "user_assertion"}:
            score += 8
        return score

    def _direct_resolution(self, query: str, relevant_set: list[dict[str, Any]]) -> dict[str, Any] | None:
        if not relevant_set:
            return None
        ordinal_tokens = ("第一个", "第一点", "第二个", "第二点", "第三个", "第三点", "前两个", "两个", "两条", "分别")
        if any(token in query for token in ordinal_tokens):
            ids = [
                str(item.get("object_id") or item.get("entry_id") or "").strip()
                for item in relevant_set
                if str(item.get("object_id") or item.get("entry_id") or "").strip()
            ]
            return {
                "resolved_target_ids": ids,
                "confidence": "high" if len(ids) == 1 else "medium",
                "strategy": "ordinal_rule",
            }
        if len(relevant_set) == 1:
            candidate = relevant_set[0]
            confidence = str(candidate.get("confidence") or "high").strip().lower()
            if confidence not in {"high", "medium"}:
                confidence = "high"
            return {
                "resolved_target_ids": [str(candidate.get("object_id") or candidate.get("entry_id") or "").strip()],
                "confidence": confidence,
                "strategy": "single_relevant_candidate",
            }
        return None
