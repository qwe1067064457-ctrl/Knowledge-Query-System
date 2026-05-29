from __future__ import annotations

import re
from typing import Any

from memory_system.session_working_memory import SessionWorkingMemoryResolver
from workflow.contracts import GlobalBindingFrame
from workflow.helpers.global_binding_prompt_helper import GlobalBindingPromptHelper

_CONTEXT_REF_PATTERN = re.compile(r"(刚才|上面|前面|这个|那个|前一个|上一条)")
_PARTIAL_SPLIT_PATTERN = re.compile(r"[？?]\s*|\n+")
_PARTIAL_CONNECTOR_PATTERN = re.compile(r"(再|顺便|另外|同时)")


class GlobalBindingWorker:
    def __init__(
        self,
        *,
        prompt_helper: GlobalBindingPromptHelper | None = None,
        working_memory_resolver: SessionWorkingMemoryResolver | None = None,
    ) -> None:
        self.prompt_helper = prompt_helper or GlobalBindingPromptHelper()
        self.working_memory_resolver = working_memory_resolver or SessionWorkingMemoryResolver()

    def build_frame(
        self,
        *,
        query: str,
        candidates: list[dict[str, Any]],
        recent_messages: list[dict[str, Any]] | None = None,
        working_memory=None,
        memory_anchors: list[dict[str, Any]] | None = None,
        llm_call: Any | None = None,
        base_dir=None,
    ) -> GlobalBindingFrame:
        recent_messages = list(recent_messages or ())
        memory_anchors = list(memory_anchors or ())
        query = query.strip()
        if not query:
            return GlobalBindingFrame()

        rule_frame = self._build_rule_frame(
            query=query,
            candidates=candidates,
            recent_messages=recent_messages,
        )
        if llm_call is None:
            return rule_frame

        working_memory_hints = self._working_memory_hints(query=query, working_memory=working_memory)
        memory_anchor_hints = self._memory_anchor_hints(memory_anchors)
        prompt = self.prompt_helper.render_prompt(
            base_dir=base_dir,
            query=query,
            rule_frame=rule_frame.to_dict(),
            recent_messages=recent_messages,
            working_memory_hints=working_memory_hints,
            memory_anchor_hints=memory_anchor_hints,
            binding_candidates=candidates,
        )
        try:
            payload = self.prompt_helper.validate_payload(
                self.prompt_helper.parse_json_payload(str(llm_call(prompt))),
                fallback_scope=rule_frame.binding_scope_hint,
            )
        except Exception:
            return GlobalBindingFrame(
                query_is_context_dependent=rule_frame.query_is_context_dependent,
                binding_scope_hint=rule_frame.binding_scope_hint,
                shared_target_candidates=rule_frame.shared_target_candidates,
                recommended_binding_mode=rule_frame.recommended_binding_mode,
                segment_hints=rule_frame.segment_hints,
                notes=tuple(rule_frame.notes) + ("llm_frame_fallback_to_rules",),
            )

        merged_notes = tuple(dict.fromkeys((*rule_frame.notes, *(str(item) for item in payload.get("notes", ())))))
        shared_candidates = tuple(payload["shared_target_candidates"]) or rule_frame.shared_target_candidates
        segment_hints = tuple(payload["segment_hints"]) or rule_frame.segment_hints
        return GlobalBindingFrame(
            query_is_context_dependent=bool(payload["query_is_context_dependent"]),
            binding_scope_hint=payload["binding_scope_hint"],  # type: ignore[arg-type]
            shared_target_candidates=shared_candidates,
            recommended_binding_mode=payload["recommended_binding_mode"],  # type: ignore[arg-type]
            segment_hints=segment_hints,
            notes=merged_notes,
        )

    def _build_rule_frame(
        self,
        *,
        query: str,
        candidates: list[dict[str, Any]],
        recent_messages: list[dict[str, Any]],
    ) -> GlobalBindingFrame:
        candidate_ids = self._shared_target_candidates(query=query, candidates=candidates)
        segments = [segment.strip() for segment in _PARTIAL_SPLIT_PATTERN.split(query) if segment.strip()]
        if len(segments) <= 1 and _PARTIAL_CONNECTOR_PATTERN.search(query):
            segments = [part.strip() for part in re.split(r"(?:再|顺便|另外|同时)", query) if part.strip()]
        segment_dependency = [self._segment_needs_context(segment) for segment in segments] or [self._segment_needs_context(query)]
        has_recent_context = bool(recent_messages)
        context_dependent = any(segment_dependency) and has_recent_context
        segment_hints = tuple(
            {
                "text": segment,
                "needs_context": needs_context,
                "segment_type": self._segment_type(segment, needs_context=needs_context),
                "context_need_type": self._context_need_type(segment, needs_context=needs_context),
                "shared_target_candidate_ids": candidate_ids if needs_context else [],
                "reason": "rule_context_reference" if needs_context else "rule_fresh_branch",
                "confidence": "medium" if needs_context else "high",
                "rewrite_hint": self._rewrite_hint(segment, needs_context=needs_context),
                "inherited_context_span": "recent_messages" if needs_context else "",
            }
            for segment, needs_context in zip(segments or [query], segment_dependency or [self._segment_needs_context(query)])
        )

        if context_dependent and candidate_ids and all(segment_dependency):
            scope = "global"
            mode = "global_only"
            notes = ("shared_context_detected", "rule_frame")
        elif context_dependent or any(segment_dependency):
            scope = "partial"
            mode = "selective_per_unit"
            notes = ("partial_context_detected", "rule_frame")
        else:
            scope = "none"
            mode = "skip"
            notes = ("rule_frame",)

        return GlobalBindingFrame(
            query_is_context_dependent=context_dependent,
            binding_scope_hint=scope,
            shared_target_candidates=tuple(candidate_ids),
            recommended_binding_mode=mode,
            segment_hints=segment_hints,
            notes=notes,
        )

    def _segment_needs_context(self, segment: str) -> bool:
        return bool(_CONTEXT_REF_PATTERN.search(segment))

    def _segment_type(self, segment: str, *, needs_context: bool) -> str:
        normalized = segment.strip()
        if "比较" in normalized:
            return "comparison_branch"
        if any(token in normalized for token in ("总结", "汇总", "归纳")):
            return "synthesis_branch"
        if needs_context:
            return "follow_up_targeted"
        if _PARTIAL_CONNECTOR_PATTERN.search(normalized):
            return "continuation"
        return "fresh_task"

    def _context_need_type(self, segment: str, *, needs_context: bool) -> str:
        if not needs_context:
            return "none"
        if any(token in segment for token in ("这个", "那个", "刚才", "上面", "前面")):
            return "reference_recovery"
        return "task_continuity"

    def _rewrite_hint(self, segment: str, *, needs_context: bool) -> str:
        if not needs_context:
            return ""
        return f"结合最近上下文重写该片段: {segment}"

    def _shared_target_candidates(self, *, query: str, candidates: list[dict[str, Any]]) -> list[str]:
        matched: list[str] = []
        lowered_query = query.lower()
        for candidate in candidates:
            object_id = str(candidate.get("object_id") or "").strip()
            content = str(candidate.get("content") or "").strip()
            if not object_id and not content:
                continue
            if object_id and object_id.lower() in lowered_query:
                matched.append(object_id)
                continue
            if content and content.lower() in lowered_query:
                matched.append(object_id or content)
                continue
            content_tokens = re.findall(r"[\u4e00-\u9fff]{2,8}|[A-Za-z0-9_]{3,}", content)
            overlap = [token for token in content_tokens if token.lower() in lowered_query]
            if len(set(overlap)) >= 2:
                matched.append(object_id or content)
        deduped: list[str] = []
        for item in matched:
            if item and item not in deduped:
                deduped.append(item)
        return deduped

    def _working_memory_hints(self, *, query: str, working_memory) -> list[dict[str, Any]]:
        entries = self.working_memory_resolver.build_relevant_entries(
            query=query,
            working_memory=working_memory,
            max_candidates=5,
        )
        return [
            {
                "entry_id": entry.entry_id,
                "entry_type": entry.entry_type,
                "content": entry.content,
                "confidence": entry.confidence,
                "structured_payload": dict(entry.structured_payload),
            }
            for entry in entries
        ]

    def _memory_anchor_hints(self, anchors: list[dict[str, Any]]) -> list[dict[str, Any]]:
        hints: list[dict[str, Any]] = []
        for item in anchors[:5]:
            hints.append(
                {
                    "anchor_id": str(item.get("anchor_id") or item.get("source_session_id") or "").strip(),
                    "summary": str(item.get("summary") or item.get("content") or "").strip(),
                    "confidence": str(item.get("confidence") or "medium").strip(),
                }
            )
        return hints
