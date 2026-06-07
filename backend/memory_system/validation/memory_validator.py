from __future__ import annotations

import math
import re
from typing import Any, Dict, Iterable, Optional


def _tokenize(text: str) -> set[str]:
    return set(re.findall(r"[\u4e00-\u9fff]|[A-Za-z0-9_]+", (text or "").lower()))


class MemoryValidator:
    """代码级 validator：schema、anchor、重复性。"""

    def validate_core(self, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        content = str(payload.get("content") or "").strip()
        scope = str(payload.get("scope") or "").strip()
        if not content or scope not in {"user_global", "user_group"}:
            return None
        return payload

    def validate_daily_log(
        self,
        payload: Dict[str, Any],
        *,
        recent_entries: Iterable[Any],
    ) -> Optional[Dict[str, Any]]:
        content = str(payload.get("content") or "").strip()
        if not content:
            return None
        if self._is_highly_duplicate(content, recent_entries):
            return None
        payload["content"] = content
        return payload

    def validate_domain_case(
        self,
        payload: Dict[str, Any],
        *,
        recent_entries: Iterable[Any],
    ) -> Optional[Dict[str, Any]]:
        title = str(payload.get("title") or "").strip()
        content = str(payload.get("content") or "").strip()
        scope = str(payload.get("scope") or "").strip()
        if not title or not content or scope != "user_group":
            return None
        if self._is_highly_duplicate(f"{title}\n{content}", recent_entries):
            return None
        payload["title"] = title
        payload["content"] = content
        return payload

    def _is_highly_duplicate(self, content: str, entries: Iterable[Any], *, threshold: float = 0.9) -> bool:
        current = _tokenize(content)
        if not current:
            return True
        for entry in entries:
            candidate_text = str(getattr(entry, "content", "") or "").strip()
            if not candidate_text:
                continue
            if candidate_text == content:
                return True
            overlap = self._jaccard(current, _tokenize(candidate_text))
            if overlap >= threshold:
                return True
        return False

    @staticmethod
    def _jaccard(left: set[str], right: set[str]) -> float:
        if not left or not right:
            return 0.0
        union = left | right
        if not union:
            return 0.0
        return len(left & right) / max(1, len(union))
