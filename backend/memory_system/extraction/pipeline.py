from __future__ import annotations

import json
import re
from typing import Any, Callable


class MemoryExtractionPipeline:
    """模型驱动的 memory extractor，缺省时安全回退到规则抽取。"""

    def __init__(self, llm_call: Callable[[str], str] | None = None) -> None:
        self._llm_call = llm_call

    def set_model_call(self, llm_call: Callable[[str], str] | None) -> None:
        self._llm_call = llm_call

    def extract_core_candidates(
            self,
            *,
            messages: list[dict[str, Any]],
            explicit_markers: list[str],
            min_len: int,
            max_len: int,
            split_sentences: Callable[[str], list[str]],
    ) -> list[dict[str, Any]]:
        candidates: list[dict[str, Any]] = []
        for message in messages:
            if message.get("role") != "user":
                continue
            scope_hint = "user_group" if str(
                message.get("memory_scope") or "").strip() == "user_group" else "user_global"
            for sentence in split_sentences(str(message.get("content") or "")):
                if len(sentence) < min_len or len(sentence) > max_len:
                    continue
                if not any(marker in sentence for marker in explicit_markers):
                    continue
                extracted = self._extract_core_with_model(sentence=sentence, scope_hint=scope_hint)
                if extracted is None:
                    extracted = self._fallback_core(sentence=sentence, scope_hint=scope_hint)
                candidates.append(extracted)
        return candidates

    def extract_daily_log(
            self,
            *,
            messages: list[dict[str, Any]],
            compaction_summary: str,
            subject: str,
            anchor_spans: list[dict[str, Any]],
            source_session_id: str | None,
    ) -> dict[str, Any]:
        extracted = self._extract_daily_log_with_model(
            messages=messages,
            compaction_summary=compaction_summary,
            subject=subject,
            anchor_spans=anchor_spans,
            source_session_id=source_session_id,
        )
        return extracted or self._fallback_daily_log(
            messages=messages,
            compaction_summary=compaction_summary,
            subject=subject,
            anchor_spans=anchor_spans,
            source_session_id=source_session_id,
        )

    def extract_domain_case(
            self,
            *,
            group_id: str,
            messages: list[dict[str, Any]],
            summary: str,
            source_session_id: str | None,
            anchor_spans: list[dict[str, Any]],
            looks_like_completed_result: Callable[[str], bool],
            looks_like_case_body: Callable[[str], bool],
    ) -> dict[str, Any] | None:
        source_text = summary.strip()
        if not source_text or not looks_like_completed_result(source_text) or not looks_like_case_body(source_text):
            source_text = self._select_case_source_text(messages)
            if not source_text or not looks_like_completed_result(source_text) or not looks_like_case_body(source_text):
                return None

        extracted = self._extract_domain_case_with_model(
            group_id=group_id,
            source_text=source_text,
            source_session_id=source_session_id,
            anchor_spans=anchor_spans,
        )
        return extracted or self._fallback_domain_case(
            group_id=group_id,
            source_text=source_text,
            source_session_id=source_session_id,
            anchor_spans=anchor_spans,
        )

    def _extract_core_with_model(self, *, sentence: str, scope_hint: str) -> dict[str, Any] | None:
        payload = self._call_json_model(
            f"""
你是 memory extractor。请把下面这句话抽取成 core memory。
要求：
1. 只输出 JSON，不要解释。
2. scope 只能是 user_global 或 user_group。
3. content 保留简洁原意。
4. subject 用短语表示主题。
输入句子：{sentence}
scope_hint: {scope_hint}
输出格式：
{{
  "memory_type": "core",
  "scope": "user_global",
  "subject": "response_style",
  "content": "默认使用中文回答。",
  "confidence": 0.9
}}
""".strip()
        )
        if not payload:
            return None
        content = str(payload.get("content") or "").strip()
        scope = str(payload.get("scope") or scope_hint).strip()
        if not content or scope not in {"user_global", "user_group"}:
            return None
        return {
            "memory_type": "core",
            "scope": scope,
            "subject": str(payload.get("subject") or self._derive_subject(sentence)).strip(),
            "content": content,
            "confidence": self._clamp_confidence(payload.get("confidence"), default=0.82),
            "anchor_spans": [],
        }

    def _extract_daily_log_with_model(
            self,
            *,
            messages: list[dict[str, Any]],
            compaction_summary: str,
            subject: str,
            anchor_spans: list[dict[str, Any]],
            source_session_id: str | None,
    ) -> dict[str, Any] | None:
        conversation_material = self._build_recent_conversation_material(messages)
        payload = self._call_json_model(
            f"""
你是 daily_log extractor。请把下面最近对话材料抽取成 daily_log。
要求：
1. 只输出 JSON，不要解释。
2. memory_type 固定 daily_log，scope 固定 user_group。
3. content 使用简洁中文保留阶段结论、关键进展或当前约束。
4. 不要把长期偏好抽成 daily_log，也不要把案例标题抽成 daily_log。
最近对话材料：
{conversation_material}
compaction_summary:
{compaction_summary}
主题提示：{subject}
输出格式：
{{
  "memory_type": "daily_log",
  "scope": "user_group",
  "subject": "阶段主题",
  "content": "阶段性摘要",
  "confidence": 0.8
}}
""".strip()
        )
        if not payload:
            return None
        content = str(payload.get("content") or "").strip()
        if not content:
            return None
        return {
            "memory_type": "daily_log",
            "scope": "user_group",
            "subject": str(payload.get("subject") or subject).strip() or "conversation_checkpoint",
            "content": content,
            "confidence": self._clamp_confidence(payload.get("confidence"), default=0.76),
            "source_session_id": source_session_id,
            "anchor_spans": anchor_spans,
        }

    def _extract_domain_case_with_model(
            self,
            *,
            group_id: str,
            source_text: str,
            source_session_id: str | None,
            anchor_spans: list[dict[str, Any]],
    ) -> dict[str, Any] | None:
        payload = self._call_json_model(
            f"""
你是 memory extractor。请把下面内容抽取成 domain_case。
要求：
1. 只输出 JSON，不要解释。
2. memory_type 固定 domain_case，scope 固定 user_group。
3. 需要 title、subject、content。
4. content 保留案例结论和主体分析，不要过短。
group_id: {group_id}
输入内容：{source_text}
输出格式：
{{
  "memory_type": "domain_case",
  "scope": "user_group",
  "title": "案例标题",
  "subject": "案例主题",
  "content": "案例内容",
  "confidence": 0.86
}}
""".strip()
        )
        if not payload:
            return None
        title = str(payload.get("title") or "").strip()
        content = str(payload.get("content") or "").strip()
        if not title or not content:
            return None
        return {
            "memory_type": "domain_case",
            "scope": "user_group",
            "title": title,
            "subject": str(payload.get("subject") or self._derive_subject(title)).strip(),
            "content": content,
            "confidence": self._clamp_confidence(payload.get("confidence"), default=0.84),
            "source_session_id": source_session_id,
            "anchor_spans": anchor_spans,
        }

    def _fallback_core(self, *, sentence: str, scope_hint: str) -> dict[str, Any]:
        return {
            "memory_type": "core",
            "scope": scope_hint,
            "subject": self._derive_subject(sentence),
            "content": sentence.strip(),
            "confidence": 0.72,
            "anchor_spans": [],
        }

    def _fallback_daily_log(
            self,
            *,
            messages: list[dict[str, Any]],
            compaction_summary: str,
            subject: str,
            anchor_spans: list[dict[str, Any]],
            source_session_id: str | None,
    ) -> dict[str, Any]:
        content = compaction_summary.strip() or self._build_recent_conversation_material(messages)
        return {
            "memory_type": "daily_log",
            "scope": "user_group",
            "subject": subject or "conversation_checkpoint",
            "content": content.strip(),
            "confidence": 0.68,
            "source_session_id": source_session_id,
            "anchor_spans": anchor_spans,
        }

    def _fallback_domain_case(
            self,
            *,
            group_id: str,
            source_text: str,
            source_session_id: str | None,
            anchor_spans: list[dict[str, Any]],
    ) -> dict[str, Any]:
        title_seed = self._derive_subject(source_text)
        return {
            "memory_type": "domain_case",
            "scope": "user_group",
            "title": f"{group_id}::{title_seed[:48]}",
            "subject": title_seed,
            "content": source_text.strip(),
            "confidence": 0.74,
            "source_session_id": source_session_id,
            "anchor_spans": anchor_spans,
        }

    def _select_case_source_text(self, messages: list[dict[str, Any]]) -> str:
        for message in reversed(messages):
            content = str(message.get("content") or "").strip()
            if content:
                return content
        return ""

    def _call_json_model(self, prompt: str) -> dict[str, Any] | None:
        if self._llm_call is None:
            return None
        try:
            raw = str(self._llm_call(prompt) or "").strip()
        except Exception:
            return None
        if not raw:
            return None
        payload = self._extract_json_payload(raw)
        return payload if isinstance(payload, dict) else None

    def _extract_json_payload(self, text: str) -> dict[str, Any] | None:
        fenced = re.findall(r"```(?:json)?\s*(\{.*?\})\s*```", text, flags=re.DOTALL)
        candidates = fenced or re.findall(r"(\{.*\})", text, flags=re.DOTALL)
        for candidate in candidates:
            try:
                parsed = json.loads(candidate)
            except json.JSONDecodeError:
                continue
            if isinstance(parsed, dict):
                return parsed
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            return None
        return parsed if isinstance(parsed, dict) else None

    def _derive_subject(self, text: str) -> str:
        compact = re.sub(r"\s+", " ", text.strip())
        compact = re.sub(r"[。！？!?；;]+$", "", compact)
        return compact[:48] or "memory_subject"

    def _build_recent_conversation_material(self, messages: list[dict[str, Any]], *, keep_last: int = 8) -> str:
        rows: list[str] = []
        for message in messages[-keep_last:]:
            role = str(message.get("role") or "assistant")
            content = str(message.get("content") or "").strip()
            if content:
                rows.append(f"{role}: {content}")
        return "\n".join(rows).strip()

    @staticmethod
    def _clamp_confidence(value: Any, *, default: float) -> float:
        try:
            parsed = float(value)
        except (TypeError, ValueError):
            return default
        return max(0.0, min(1.0, parsed))
