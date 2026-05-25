from __future__ import annotations

import json
from pathlib import Path
from typing import Any


_DEFAULT_STATE_UPDATE_PROMPT = """你是一个会话短程状态更新器。

请根据最近对话、上一轮状态和高可靠候选对象，更新当前会话的短程运行态。

要求：
1. 只保留真正会影响下一轮检索或 challenge 的短程焦点。
2. 不要编造候选列表中不存在的对象。
3. 如果当前无法稳定聚焦，也要如实降低 resolution_confidence。
4. 只输出 JSON。

输出 JSON 字段：
{
  "focus_question_object_id": "字符串或 null",
  "focus_question_object_text": "字符串或 null",
  "focus_predicate": "字符串或 null",
  "recent_question_objects": [{"object_id":"...", "content":"..."}],
  "recent_evidence_topics": ["..."],
  "resolution_confidence": "high|medium|low",
  "last_update_reason": "简短原因"
}

上一轮状态：
{previous_state_json}

最近对话：
{recent_messages_json}

候选问题对象：
{question_candidates_json}

候选证据主题：
{evidence_topics_json}

当前用户问题：
{query}
"""

_DEFAULT_REWRITE_PROMPT = """你是一个 context binding 解析助手。

目标：根据最近对话与候选对象，筛出最相关对象，并把当前用户问题改写成可检索、可 challenge 的独立查询。

要求：
1. 优先选择最相关对象，避免宽泛多目标噪音。
2. 如果无法稳定解析，必须返回 needs_clarification=true，并给出 fallback_type 与 reason。
3. 不要添加对话中不存在的新事实。
4. 只输出 JSON。

输出 JSON 字段：
{
  "resolved_target_ids": ["object_id"],
  "rewritten_query": "改写后的独立查询",
  "confidence": "high|medium|low",
  "needs_clarification": true/false,
  "fallback_type": "needs_clarification|rewrite_without_target|retrieve_on_raw_query|answer_from_context_only|null",
  "reason": "简短原因"
}

当前 state / 上下文摘要：
{binding_context_json}

最近对话：
{recent_messages_json}

候选相关对象 / 候选问题对象：
{question_candidates_json}

当前用户问题：
{query}
"""


class BoundQueryPromptHelper:
    STATE_UPDATE_REQUIRED_KEYS = (
        "focus_question_object_id",
        "focus_question_object_text",
        "focus_predicate",
        "recent_question_objects",
        "recent_evidence_topics",
        "resolution_confidence",
        "last_update_reason",
    )
    REWRITE_REQUIRED_KEYS = (
        "resolved_target_ids",
        "rewritten_query",
        "confidence",
        "needs_clarification",
        "fallback_type",
        "reason",
    )

    def load_state_update_prompt(self, base_dir: Path | None) -> str:
        return self._load_prompt(
            base_dir,
            filename="state_update_prompt.md",
            fallback=_DEFAULT_STATE_UPDATE_PROMPT,
        )

    def load_rewrite_prompt(self, base_dir: Path | None) -> str:
        return self._load_prompt(
            base_dir,
            filename="bound_query_rewrite_prompt.md",
            fallback=_DEFAULT_REWRITE_PROMPT,
        )

    def render_state_update_prompt(
        self,
        *,
        base_dir: Path | None,
        query: str,
        previous_state: dict[str, Any],
        recent_messages: list[dict[str, Any]],
        question_candidates: list[dict[str, Any]],
        evidence_topics: list[str],
    ) -> str:
        template = self.load_state_update_prompt(base_dir)
        return (
            template
            .replace("{query}", query)
            .replace("{previous_state_json}", self._json(previous_state))
            .replace("{recent_messages_json}", self._json(recent_messages[-6:]))
            .replace("{question_candidates_json}", self._json(question_candidates[:6]))
            .replace("{evidence_topics_json}", self._json(evidence_topics[:6]))
        )

    def render_rewrite_prompt(
        self,
        *,
        base_dir: Path | None,
        query: str,
        binding_context: dict[str, Any] | None = None,
        state: dict[str, Any] | None = None,
        recent_messages: list[dict[str, Any]],
        question_candidates: list[dict[str, Any]],
    ) -> str:
        template = self.load_rewrite_prompt(base_dir)
        context_payload = dict(binding_context or state or {})
        return (
            template
            .replace("{query}", query)
            .replace("{binding_context_json}", self._json(context_payload))
            .replace("{recent_messages_json}", self._json(recent_messages[-6:]))
            .replace("{question_candidates_json}", self._json(question_candidates[:6]))
        )

    def parse_json_payload(self, content: str) -> dict[str, Any]:
        text = content.strip()
        if text.startswith("```"):
            lines = [line for line in text.splitlines() if not line.startswith("```")]
            text = "\n".join(lines).strip()
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            text = text[start : end + 1]
        return json.loads(text)

    def validate_state_update_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        data = dict(payload or {})
        normalized = {
            "focus_question_object_id": data.get("focus_question_object_id"),
            "focus_question_object_text": data.get("focus_question_object_text"),
            "focus_predicate": data.get("focus_predicate"),
            "recent_question_objects": [
                {
                    "object_id": str(item.get("object_id") or "").strip(),
                    "content": str(item.get("content") or "").strip(),
                }
                for item in data.get("recent_question_objects", []) or []
                if str(item.get("object_id") or "").strip() and str(item.get("content") or "").strip()
            ],
            "recent_evidence_topics": [
                str(item).strip()
                for item in data.get("recent_evidence_topics", []) or []
                if str(item).strip()
            ],
            "resolution_confidence": str(data.get("resolution_confidence", "low")).strip().lower(),
            "last_update_reason": str(data.get("last_update_reason") or "").strip() or None,
        }
        if normalized["resolution_confidence"] not in {"high", "medium", "low"}:
            normalized["resolution_confidence"] = "low"
        return normalized

    def validate_rewrite_payload(self, payload: dict[str, Any], *, original_query: str) -> dict[str, Any]:
        data = dict(payload or {})
        confidence = str(data.get("confidence", "medium")).strip().lower()
        if confidence not in {"high", "medium", "low"}:
            confidence = "medium"
        rewritten_query = str(data.get("rewritten_query") or original_query).strip() or original_query
        fallback_type = data.get("fallback_type")
        if fallback_type is not None:
            fallback_type = str(fallback_type).strip() or None
        reason = data.get("reason")
        if reason is not None:
            reason = str(reason).strip() or None
        return {
            "resolved_target_ids": [
                str(item).strip()
                for item in data.get("resolved_target_ids", ()) or []
                if str(item).strip()
            ],
            "rewritten_query": rewritten_query,
            "confidence": confidence,
            "needs_clarification": bool(data.get("needs_clarification", False)),
            "fallback_type": fallback_type,
            "reason": reason,
        }

    def _load_prompt(self, base_dir: Path | None, *, filename: str, fallback: str) -> str:
        if base_dir is None:
            return fallback
        prompt_path = base_dir / "prompts" / "workflow" / filename
        if prompt_path.exists():
            return prompt_path.read_text(encoding="utf-8").strip()
        return fallback

    def _json(self, payload: Any) -> str:
        return json.dumps(payload, ensure_ascii=False, indent=2)
