from __future__ import annotations

from typing import Any


class CoreGate:
    def select_candidate_messages(self, messages: list[dict[str, Any]], *, explicit_markers: list[str]) -> list[dict[str, Any]]:
        selected: list[dict[str, Any]] = []
        for message in messages:
            if message.get("role") != "user":
                continue
            content = str(message.get("content") or "").strip()
            if not content:
                continue
            if explicit_markers and not any(marker in content for marker in explicit_markers):
                continue
            selected.append(message)
        return selected


class DailyLogGate:
    def should_extract(self, *, checkpoint_enabled: bool, messages: list[dict[str, Any]], compaction_summary: str) -> bool:
        if not checkpoint_enabled:
            return False
        if compaction_summary.strip() and compaction_summary.strip() != "NO_REPLY":
            return True
        return any(str(message.get("content") or "").strip() for message in messages if message.get("role") in {"user", "assistant"})


class DomainCaseGate:
    def should_extract(
        self,
        *,
        messages: list[dict[str, Any]],
        compaction_summary: str,
        looks_like_completed_result,
        looks_like_case_body,
    ) -> bool:
        source_text = compaction_summary.strip()
        if source_text and looks_like_completed_result(source_text) and looks_like_case_body(source_text):
            return True
        for message in reversed(messages):
            content = str(message.get("content") or "").strip()
            if content and looks_like_completed_result(content) and looks_like_case_body(content):
                return True
        return False
