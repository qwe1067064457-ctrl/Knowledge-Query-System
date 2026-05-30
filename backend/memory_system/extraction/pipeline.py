from __future__ import annotations

from typing import Any, Dict, List, Optional, cast

from context.models import MemoryScope


class MemoryExtractionPipeline:
    """受控的 memory extractor。当前先走规则+最小结构抽取，不做自由 agent。"""

    def extract_daily_log(
        self,
        *,
        summary: str,
        subject: str,
        anchor_spans: List[Dict[str, Any]],
        source_session_id: Optional[str],
    ) -> Optional[Dict[str, Any]]:
        cleaned = summary.strip()
        if not cleaned or cleaned == "NO_REPLY":
            return None
        return {
            "memory_type": "daily_log",
            "scope": "user_group",
            "content": cleaned,
            "subject": subject.strip() or "conversation_checkpoint",
            "confidence": 0.7 if anchor_spans else 0.5,
            "source_session_id": source_session_id,
            "anchor_spans": anchor_spans,
        }

    def extract_core_candidates(
        self,
        *,
        messages: List[Dict[str, Any]],
        explicit_markers: List[str],
        min_len: int,
        max_len: int,
        split_sentences,
    ) -> List[Dict[str, Any]]:
        candidates: List[Dict[str, Any]] = []
        seen: set[str] = set()
        for message in messages:
            if message.get("role") != "user":
                continue
            content = str(message.get("content", "") or "").strip()
            for sentence in split_sentences(content):
                if not any(marker in sentence for marker in explicit_markers):
                    continue
                if len(sentence) < min_len or len(sentence) > max_len:
                    continue
                scope: MemoryScope = "user_global"
                if str(message.get("memory_scope") or "").strip() == "user_group":
                    scope = "user_group"
                signature = f"{scope}:{sentence}"
                if signature in seen:
                    continue
                seen.add(signature)
                candidates.append(
                    {
                        "memory_type": "core",
                        "scope": cast(str, scope),
                        "content": sentence,
                    }
                )
        return candidates

    def extract_domain_case(
        self,
        *,
        group_id: str,
        messages: List[Dict[str, Any]],
        summary: str,
        source_session_id: Optional[str],
        anchor_spans: List[Dict[str, Any]],
        looks_like_completed_result,
        looks_like_case_body,
    ) -> Optional[Dict[str, Any]]:
        source_text = summary.strip()
        if not source_text:
            for message in reversed(messages):
                if message.get("role") == "assistant" and message.get("content"):
                    source_text = str(message["content"]).strip()
                    break
        if not source_text:
            return None
        if not looks_like_completed_result(source_text):
            return None
        if not looks_like_case_body(source_text):
            return None

        title_seed = ""
        for message in reversed(messages):
            if message.get("role") == "user" and message.get("content"):
                title_seed = str(message["content"]).strip()
                break
        title_seed = title_seed[:24] if title_seed else "会话案例"
        return {
            "memory_type": "domain_case",
            "scope": "user_group",
            "title": f"{group_id}::{title_seed}",
            "content": source_text,
            "subject": title_seed,
            "confidence": 0.85,
            "source_session_id": source_session_id,
            "anchor_spans": anchor_spans,
        }
