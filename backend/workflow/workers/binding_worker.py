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
