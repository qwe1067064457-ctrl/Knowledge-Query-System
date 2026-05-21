from __future__ import annotations

import re
from typing import Any


class BindingWorker:
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

    def bind(self, *, query: str, candidates: list[dict[str, Any]]) -> dict[str, Any]:
        if not candidates:
            return {"binding_ambiguous": True, "bound_targets": ()}
        if self._should_bind_multiple(query, candidates):
            selected = tuple(candidates[: self._multi_target_limit(query, candidates)])
            return {
                "binding_ambiguous": False,
                "bound_targets": selected,
                "binding_confidence": "medium",
                "notes": ("worker_binding_multi",),
            }
        return {
            "binding_ambiguous": False,
            "bound_targets": (candidates[-1],),
            "binding_confidence": "medium",
            "notes": ("worker_binding",),
        }

    def _should_bind_multiple(self, query: str, candidates: list[dict[str, Any]]) -> bool:
        if len(candidates) < 2:
            return False
        return any(pattern.search(query) for pattern in self._MULTI_TARGET_PATTERNS)

    def _multi_target_limit(self, query: str, candidates: list[dict[str, Any]]) -> int:
        if "前两个" in query or "两个" in query or "两条" in query:
            return 2
        return min(len(candidates), 3)
