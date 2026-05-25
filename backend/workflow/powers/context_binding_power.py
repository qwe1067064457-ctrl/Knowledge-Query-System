from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from context.models import SessionDialogueState
from workflow.helpers.binding_response_helper import BindingResponseHelper
from workflow.helpers.bound_query_prompt_helper import BoundQueryPromptHelper
from workflow.types import ContextBindingResult
from workflow.workers.binding_worker import BindingWorker


class ContextBindingPower:
    _EXPLICIT_PATTERNS = (
        re.compile(r"(这个|那个|上面那个|你刚才说的)"),
        re.compile(r"(前两个|第二种|后一种)"),
    )
    _MULTI_TARGET_PATTERNS = (
        re.compile(r"前两个"),
        re.compile(r"两个"),
        re.compile(r"两条"),
        re.compile(r"分别"),
        re.compile(r"这些"),
        re.compile(r"都"),
    )

    def __init__(
        self,
        response_helper: BindingResponseHelper | None = None,
        binding_worker: BindingWorker | None = None,
        prompt_helper: BoundQueryPromptHelper | None = None,
    ) -> None:
        self.response_helper = response_helper or BindingResponseHelper()
        self.binding_worker = binding_worker or BindingWorker()
        self.prompt_helper = prompt_helper or BoundQueryPromptHelper()

    def collect_candidates(self, entries: list[dict[str, Any]], *, limit: int = 20) -> list[dict[str, Any]]:
        candidates: list[dict[str, Any]] = []
        for entry in reversed(entries):
            candidates.append(dict(entry))
            if len(candidates) >= limit:
                break
        return list(reversed(candidates))

    def bind(
        self,
        query: str,
        candidates: list[dict[str, Any]],
        *,
        dialogue_state: SessionDialogueState | dict[str, Any] | None = None,
        recent_messages: list[dict[str, Any]] | None = None,
        llm_call: Any | None = None,
        base_dir: Path | None = None,
        rewrite_query: bool = False,
        recent_power: str | None = None,
        recent_object_type: str | None = None,
    ) -> ContextBindingResult:
        state = self._normalize_state(dialogue_state)
        candidate_pool = self._merge_candidates_with_state(candidates, state)
        recent_messages = list(recent_messages or ())
        current_state = self._update_dialogue_state(
            query=query,
            candidates=candidate_pool,
            previous_state=state,
            recent_messages=recent_messages,
            llm_call=llm_call,
            base_dir=base_dir,
        )

        if not candidate_pool:
            return self._build_ambiguity_result(
                query=query,
                candidates=[],
                state=current_state,
                reason="no_candidates",
            )

        rule_result = self.binding_worker.select_targets(
            query=query,
            candidates=candidate_pool,
            focus_object_id=current_state.focus_question_object_id,
        )
        if not rule_result["binding_ambiguous"] and rule_result["binding_confidence"] == "high":
            targets = tuple(rule_result["selected_targets"])
            rewritten_query = self._maybe_rewrite_query(
                query=query,
                targets=targets,
                state=current_state,
                recent_messages=recent_messages,
                llm_call=llm_call,
                base_dir=base_dir,
                rewrite_query=rewrite_query,
            )
            return self._build_success_result(
                targets=targets,
                confidence="high",
                strategy=str(rule_result.get("matched_by") or "rule_binding"),
                state=current_state,
                rewritten_query=rewritten_query,
                notes=tuple(str(item) for item in rule_result.get("notes", ()) or ()),
            )

        llm_resolution = None
        if self._should_use_llm_resolution(query=query, llm_call=llm_call, candidates=candidate_pool):
            llm_resolution = self._resolve_with_llm(
                query=query,
                candidates=candidate_pool,
                state=current_state,
                recent_messages=recent_messages,
                llm_call=llm_call,
                base_dir=base_dir,
            )
            if llm_resolution and not llm_resolution.get("needs_clarification", False):
                targets = self._resolve_target_ids(
                    candidate_pool,
                    llm_resolution.get("resolved_target_ids", ()),
                )
                if targets:
                    return self._build_success_result(
                        targets=tuple(targets),
                        confidence=str(llm_resolution.get("confidence", "medium")),
                        strategy="llm_resolution",
                        state=current_state,
                        rewritten_query=str(llm_resolution.get("rewritten_query") or query).strip(),
                        notes=("llm_resolution",),
                    )

        if not rule_result["binding_ambiguous"] and rule_result["binding_confidence"] == "medium":
            targets = tuple(rule_result["selected_targets"])
            rewritten_query = self._maybe_rewrite_query(
                query=query,
                targets=targets,
                state=current_state,
                recent_messages=recent_messages,
                llm_call=llm_call,
                base_dir=base_dir,
                rewrite_query=rewrite_query,
            )
            return self._build_success_result(
                targets=targets,
                confidence="medium",
                strategy=str(rule_result.get("matched_by") or "rule_binding"),
                state=current_state,
                rewritten_query=rewritten_query,
                notes=tuple(str(item) for item in rule_result.get("notes", ()) or ()),
            )

        if len(query.strip()) <= 20 and recent_power:
            for candidate in reversed(candidate_pool):
                if recent_object_type and candidate.get("object_type") != recent_object_type:
                    continue
                if candidate.get("source_power") == recent_power:
                    rewritten_query = self._maybe_rewrite_query(
                        query=query,
                        targets=(candidate,),
                        state=current_state,
                        recent_messages=recent_messages,
                        llm_call=llm_call,
                        base_dir=base_dir,
                        rewrite_query=rewrite_query,
                    )
                    return self._build_success_result(
                        targets=(candidate,),
                        confidence="medium",
                        strategy="topic_continuity",
                        state=current_state,
                        rewritten_query=rewritten_query,
                        notes=("topic_continuity",),
                    )

        reason = "binding_ambiguous"
        if llm_resolution and llm_resolution.get("needs_clarification", False):
            reason = "llm_resolution_needs_clarification"
        elif rule_result.get("ambiguity_reason"):
            reason = str(rule_result["ambiguity_reason"])
        return self._build_ambiguity_result(
            query=query,
            candidates=candidate_pool,
            state=current_state,
            reason=reason,
        )

    def _select_primary_target(self, candidates: list[dict[str, Any]]) -> dict[str, Any]:
        for candidate in reversed(candidates):
            if candidate.get("object_type") != "evidence_ref":
                return candidate
        return candidates[-1]

    def _select_targets_for_query(self, query: str, candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if len(candidates) < 2 or not any(pattern.search(query) for pattern in self._MULTI_TARGET_PATTERNS):
            return [self._select_primary_target(candidates)]
        if "前两个" in query or "两个" in query or "两条" in query:
            return list(candidates[:2])
        return list(candidates[: min(len(candidates), 3)])

    def _normalize_state(self, state: SessionDialogueState | dict[str, Any] | None) -> SessionDialogueState:
        if isinstance(state, SessionDialogueState):
            return state
        return SessionDialogueState.from_dict(state)

    def _merge_candidates_with_state(
        self,
        candidates: list[dict[str, Any]],
        state: SessionDialogueState,
    ) -> list[dict[str, Any]]:
        merged: list[dict[str, Any]] = []
        seen: set[str] = set()
        for item in state.recent_question_objects:
            object_id = str(item.get("object_id") or "").strip()
            if not object_id or object_id in seen:
                continue
            seen.add(object_id)
            merged.append(dict(item))
        for item in candidates:
            object_id = str(item.get("object_id") or "").strip()
            key = object_id or str(item.get("content") or "")
            if key in seen:
                continue
            seen.add(key)
            merged.append(dict(item))
        return merged

    def _update_dialogue_state(
        self,
        *,
        query: str,
        candidates: list[dict[str, Any]],
        previous_state: SessionDialogueState,
        recent_messages: list[dict[str, Any]],
        llm_call: Any | None,
        base_dir: Path | None,
    ) -> SessionDialogueState:
        fallback = self._fallback_state(
            query=query,
            candidates=candidates,
            previous_state=previous_state,
        )
        if llm_call is None:
            return fallback
        try:
            prompt = self.prompt_helper.render_state_update_prompt(
                base_dir=base_dir,
                query=query,
                previous_state=previous_state.to_dict(),
                recent_messages=recent_messages,
                question_candidates=[
                    {
                        "object_id": item.get("object_id"),
                        "content": item.get("content"),
                        "refs": list(item.get("refs", ())),
                    }
                    for item in candidates
                ],
                evidence_topics=self._extract_evidence_topics(candidates),
            )
            payload = self.prompt_helper.parse_json_payload(str(llm_call(prompt)))
            state = SessionDialogueState.from_dict(
                self.prompt_helper.validate_state_update_payload(payload)
            )
            if not state.recent_question_objects:
                state.recent_question_objects = fallback.recent_question_objects
            if not state.recent_evidence_topics:
                state.recent_evidence_topics = fallback.recent_evidence_topics
            if state.resolution_confidence not in {"high", "medium", "low"}:
                state.resolution_confidence = fallback.resolution_confidence
            return state
        except Exception:
            return fallback

    def _fallback_state(
        self,
        *,
        query: str,
        candidates: list[dict[str, Any]],
        previous_state: SessionDialogueState,
    ) -> SessionDialogueState:
        recent_question_objects = [
            {
                "object_id": str(item.get("object_id") or ""),
                "content": str(item.get("content") or ""),
                "refs": list(item.get("refs", ())),
                "source_power": item.get("source_power"),
                "object_type": item.get("object_type"),
            }
            for item in candidates[:5]
        ]
        focus = None
        if previous_state.focus_question_object_id:
            for item in recent_question_objects:
                if item["object_id"] == previous_state.focus_question_object_id:
                    focus = item
                    break
        if focus is None and len(recent_question_objects) == 1:
            focus = recent_question_objects[-1]
        return SessionDialogueState(
            focus_question_object_id=(focus or {}).get("object_id"),
            focus_question_object_text=(focus or {}).get("content"),
            focus_predicate=self._infer_predicate(query, previous_state),
            recent_question_objects=recent_question_objects,
            recent_evidence_topics=self._extract_evidence_topics(candidates),
            resolution_confidence="medium" if focus else "low",
            last_update_reason="fallback_state_update" if focus else "fallback_state_without_focus",
        )

    def _infer_predicate(self, query: str, previous_state: SessionDialogueState) -> str | None:
        text = query.strip()
        for marker in ("依据", "风险", "重量", "价格", "期限", "条件", "结论"):
            if marker in text:
                return marker
        return previous_state.focus_predicate

    def _extract_evidence_topics(self, candidates: list[dict[str, Any]]) -> list[str]:
        topics: list[str] = []
        for item in candidates:
            content = str(item.get("content") or "").strip()
            if content and content not in topics:
                topics.append(content)
        return topics[:5]

    def _should_use_llm_resolution(
        self,
        *,
        query: str,
        llm_call: Any | None,
        candidates: list[dict[str, Any]],
    ) -> bool:
        if llm_call is None or not candidates:
            return False
        if len(candidates) == 1 and not any(pattern.search(query) for pattern in self._EXPLICIT_PATTERNS):
            return False
        return any(pattern.search(query) for pattern in self._EXPLICIT_PATTERNS) or len(query.strip()) <= 40

    def _resolve_with_llm(
        self,
        *,
        query: str,
        candidates: list[dict[str, Any]],
        state: SessionDialogueState,
        recent_messages: list[dict[str, Any]],
        llm_call: Any,
        base_dir: Path | None,
    ) -> dict[str, Any] | None:
        prompt = self.prompt_helper.render_rewrite_prompt(
            base_dir=base_dir,
            query=query,
            state=state.to_dict(),
            recent_messages=recent_messages,
            question_candidates=[
                {
                    "object_id": item.get("object_id"),
                    "content": item.get("content"),
                    "refs": list(item.get("refs", ())),
                }
                for item in candidates
            ],
        )
        try:
            payload = self.prompt_helper.validate_rewrite_payload(
                self.prompt_helper.parse_json_payload(str(llm_call(prompt))),
                original_query=query,
            )
        except Exception:
            return None
        return payload

    def _resolve_target_ids(
        self,
        candidates: list[dict[str, Any]],
        resolved_target_ids: list[str] | tuple[str, ...],
    ) -> list[dict[str, Any]]:
        wanted = {str(item) for item in resolved_target_ids if item}
        if not wanted:
            return []
        selected = [item for item in candidates if str(item.get("object_id") or "") in wanted]
        return selected

    def _maybe_rewrite_query(
        self,
        *,
        query: str,
        targets: tuple[dict[str, Any], ...],
        state: SessionDialogueState,
        recent_messages: list[dict[str, Any]],
        llm_call: Any | None,
        base_dir: Path | None,
        rewrite_query: bool,
    ) -> str | None:
        if not rewrite_query:
            return None
        if llm_call is not None:
            resolution = self._resolve_with_llm(
                query=query,
                candidates=list(targets),
                state=state,
                recent_messages=recent_messages,
                llm_call=llm_call,
                base_dir=base_dir,
            )
            if resolution and not resolution.get("needs_clarification", False):
                return str(resolution.get("rewritten_query") or query).strip()
        if len(targets) == 1:
            target_text = str(targets[0].get("content") or "").strip()
            predicate = state.focus_predicate or ""
            parts = [target_text]
            if predicate and predicate not in query:
                parts.append(predicate)
            if query not in parts:
                parts.append(query)
            rewritten = " ".join(part for part in parts if part).strip()
            return rewritten or query
        return query

    def _build_success_result(
        self,
        *,
        targets: tuple[dict[str, Any], ...],
        confidence: str,
        strategy: str,
        state: SessionDialogueState,
        rewritten_query: str | None,
        notes: tuple[str, ...],
    ) -> ContextBindingResult:
        target = targets[-1]
        metadata = self.response_helper.build_success_metadata(
            strategy=strategy,
            target=target,
            confidence=confidence,
        )
        return ContextBindingResult(
            bound_targets=targets,
            binding_confidence=confidence,
            matched_by=metadata["matched_by"],
            clarification_hint=metadata["clarification_hint"],
            binding_summary=metadata["binding_summary"],
            notes=tuple(metadata["notes"]) + tuple(notes),
            rewritten_query=rewritten_query,
            state_snapshot=state.to_dict(),
        )

    def _build_ambiguity_result(
        self,
        *,
        query: str,
        candidates: list[dict[str, Any]],
        state: SessionDialogueState,
        reason: str,
    ) -> ContextBindingResult:
        metadata = self.response_helper.build_ambiguity_metadata(
            query=query,
            reason=reason,
            candidates=candidates,
        )
        return ContextBindingResult(
            binding_confidence="low",
            binding_ambiguous=True,
            matched_by=metadata["matched_by"],
            clarification_hint=metadata["clarification_hint"],
            binding_summary=metadata["binding_summary"],
            notes=tuple(metadata["notes"]),
            state_snapshot=state.to_dict(),
        )
