from __future__ import annotations

from pathlib import Path
from typing import Any

from memory_system.session_working_memory import SessionWorkingMemory, SessionWorkingMemoryResolver
from workflow.helpers.binding_response_helper import BindingResponseHelper
from workflow.helpers.bound_query_prompt_helper import BoundQueryPromptHelper
from workflow.types import ContextBindingResult
from workflow.workers.binding_worker import BindingWorker


class ContextBindingPower:
    def __init__(
        self,
        response_helper: BindingResponseHelper | None = None,
        binding_worker: BindingWorker | None = None,
        prompt_helper: BoundQueryPromptHelper | None = None,
        working_memory_resolver: SessionWorkingMemoryResolver | None = None,
    ) -> None:
        self.response_helper = response_helper or BindingResponseHelper()
        self.binding_worker = binding_worker or BindingWorker()
        self.prompt_helper = prompt_helper or BoundQueryPromptHelper()
        self.working_memory_resolver = working_memory_resolver or SessionWorkingMemoryResolver()

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
        working_memory: SessionWorkingMemory | dict[str, Any] | None = None,
        recent_messages: list[dict[str, Any]] | None = None,
        llm_call: Any | None = None,
        base_dir: Path | None = None,
        rewrite_query: bool = False,
        recent_power: str | None = None,
        recent_object_type: str | None = None,
        memory_anchors: list[dict[str, Any]] | None = None,
    ) -> ContextBindingResult:
        del recent_power, recent_object_type
        recent_messages = list(recent_messages or ())
        query_style = self.working_memory_resolver.classify_query_style(query)
        relevant_pool = self._build_relevant_pool(
            query=query,
            candidates=candidates,
            working_memory=working_memory,
            memory_anchors=memory_anchors,
        )
        filter_result = self.binding_worker.filter_relevant_set(
            query=query,
            candidates=relevant_pool,
            query_style=query_style,
            max_candidates=7,
        )
        relevant_set = [dict(item) for item in filter_result["relevant_set"]]
        direct_resolution = dict(filter_result.get("direct_resolution") or {})
        binding_snapshot = self._build_binding_snapshot(
            query=query,
            query_style=query_style,
            candidate_pool=relevant_pool,
            relevant_set=relevant_set,
        )

        if not relevant_set:
            return self._fallback_without_relevant_set(
                query=query,
                query_style=query_style,
                rewrite_query=rewrite_query,
                snapshot=binding_snapshot,
            )

        if direct_resolution:
            targets = self._resolve_target_ids(relevant_set, direct_resolution.get("resolved_target_ids", ()))
            if targets:
                rewritten_query = (
                    self._rewrite_from_single_target(query, targets[0])
                    if rewrite_query
                    else None
                )
                return self._build_success_result(
                    targets=tuple(targets),
                    relevant_set=relevant_set,
                    resolved_target_ids=tuple(str(item.get("object_id") or "") for item in targets if item.get("object_id")),
                    confidence=str(direct_resolution.get("confidence") or "high"),
                    strategy=str(direct_resolution.get("matched_by") or direct_resolution.get("strategy") or "rule_direct_resolution"),
                    rewritten_query=rewritten_query,
                    notes=tuple(str(item) for item in direct_resolution.get("notes", ()) or ()),
                    binding_snapshot=binding_snapshot,
                )

        if llm_call is None:
            return self._build_fallback_result(
                fallback_type="needs_clarification",
                reason="no_llm_resolution_available",
                candidates=relevant_set,
                confidence="low",
                binding_snapshot=binding_snapshot,
            )

        resolution = self._resolve_with_llm(
            query=query,
            relevant_set=relevant_set,
            recent_messages=recent_messages,
            llm_call=llm_call,
            base_dir=base_dir,
            binding_snapshot=binding_snapshot,
        )
        if resolution is None:
            return self._build_fallback_result(
                fallback_type="needs_clarification",
                reason="llm_resolution_failed",
                candidates=relevant_set,
                confidence="low",
                binding_snapshot=binding_snapshot,
            )

        if resolution.get("needs_clarification", False):
            return self._build_fallback_result(
                fallback_type=str(resolution.get("fallback_type") or "needs_clarification"),
                reason=str(resolution.get("reason") or "llm_resolution_needs_clarification"),
                candidates=relevant_set,
                confidence=str(resolution.get("confidence") or "low"),
                binding_snapshot=binding_snapshot,
                rewritten_query=str(resolution.get("rewritten_query") or "").strip() or None,
            )

        targets = self._resolve_target_ids(relevant_set, resolution.get("resolved_target_ids", ()))
        rewritten_query = str(resolution.get("rewritten_query") or query).strip()
        if targets:
            return self._build_success_result(
                targets=tuple(targets),
                relevant_set=relevant_set,
                resolved_target_ids=tuple(str(item.get("object_id") or "") for item in targets if item.get("object_id")),
                confidence=str(resolution.get("confidence") or "medium"),
                strategy="llm_resolution",
                rewritten_query=rewritten_query if rewrite_query or rewritten_query != query else None,
                notes=("llm_resolution",),
                binding_snapshot=binding_snapshot,
            )

        fallback_type = str(resolution.get("fallback_type") or "").strip()
        if fallback_type:
            return self._build_fallback_result(
                fallback_type=fallback_type,
                reason=str(resolution.get("reason") or "llm_resolution_without_targets"),
                candidates=relevant_set,
                confidence=str(resolution.get("confidence") or "medium"),
                binding_snapshot=binding_snapshot,
                rewritten_query=rewritten_query if rewritten_query != query else None,
            )

        return self._build_fallback_result(
            fallback_type="needs_clarification",
            reason="llm_resolution_without_targets",
            candidates=relevant_set,
            confidence=str(resolution.get("confidence") or "low"),
            binding_snapshot=binding_snapshot,
            rewritten_query=rewritten_query if rewritten_query != query else None,
        )

    def _build_relevant_pool(
        self,
        *,
        query: str,
        candidates: list[dict[str, Any]],
        working_memory: SessionWorkingMemory | dict[str, Any] | None,
        memory_anchors: list[dict[str, Any]] | None,
    ) -> list[dict[str, Any]]:
        pool: list[dict[str, Any]] = []
        seen: set[str] = set()

        for candidate in candidates:
            key = self._candidate_key(candidate)
            if key in seen:
                continue
            seen.add(key)
            pool.append(dict(candidate))

        memory_entries = self.working_memory_resolver.build_relevant_entries(
            query=query,
            working_memory=working_memory,
            max_candidates=7,
        )
        for entry in memory_entries:
            candidate = self._candidate_from_working_memory(entry)
            key = self._candidate_key(candidate)
            if key in seen:
                continue
            seen.add(key)
            pool.append(candidate)

        for anchor in memory_anchors or ():
            candidate = {
                "object_id": str(anchor.get("anchor_id") or anchor.get("source_session_id") or "").strip(),
                "object_type": "memory_anchor",
                "content": str(anchor.get("content") or anchor.get("summary") or "").strip(),
                "source_power": "memory_anchor",
                "refs": list(anchor.get("refs", ()) or ()),
                "confidence": str(anchor.get("confidence") or "medium"),
                "source_kind": "memory_anchor",
            }
            if not candidate["object_id"] and not candidate["content"]:
                continue
            key = self._candidate_key(candidate)
            if key in seen:
                continue
            seen.add(key)
            pool.append(candidate)
        return pool

    def _candidate_from_working_memory(self, entry) -> dict[str, Any]:
        return {
            "object_id": entry.entry_id,
            "object_type": entry.entry_type,
            "content": entry.content,
            "source_power": "session_working_memory",
            "refs": list(entry.structured_payload.get("refs", ()) or ()),
            "confidence": entry.confidence,
            "source_kind": entry.source_kind,
            "structured_payload": dict(entry.structured_payload),
        }

    def _candidate_key(self, candidate: dict[str, Any]) -> str:
        object_id = str(candidate.get("object_id") or "").strip()
        if object_id:
            return object_id
        return str(candidate.get("content") or "").strip()

    def _resolve_with_llm(
        self,
        *,
        query: str,
        relevant_set: list[dict[str, Any]],
        recent_messages: list[dict[str, Any]],
        llm_call: Any,
        base_dir: Path | None,
        binding_snapshot: dict[str, Any],
    ) -> dict[str, Any] | None:
        prompt = self.prompt_helper.render_rewrite_prompt(
            base_dir=base_dir,
            query=query,
            binding_context=binding_snapshot,
            recent_messages=recent_messages,
            question_candidates=[
                {
                    "object_id": item.get("object_id"),
                    "content": item.get("content"),
                    "object_type": item.get("object_type"),
                    "source_kind": item.get("source_kind"),
                }
                for item in relevant_set
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
        wanted = {str(item).strip() for item in resolved_target_ids if str(item).strip()}
        if not wanted:
            return []
        selected = [item for item in candidates if str(item.get("object_id") or "").strip() in wanted]
        return selected

    def _rewrite_from_single_target(self, query: str, target: dict[str, Any]) -> str:
        target_text = str(target.get("content") or target.get("object_id") or "").strip()
        if not target_text:
            return query
        if query.strip() in target_text:
            return target_text
        return f"{target_text} {query.strip()}".strip()

    def _build_binding_snapshot(
        self,
        *,
        query: str,
        query_style: str,
        candidate_pool: list[dict[str, Any]],
        relevant_set: list[dict[str, Any]],
    ) -> dict[str, Any]:
        return {
            "query": query,
            "query_style": query_style,
            "candidate_count": len(candidate_pool),
            "candidate_pool_size": len(candidate_pool),
            "relevant_set_size": len(relevant_set),
            "relevant_target_ids": [
                str(item.get("object_id") or "").strip()
                for item in relevant_set
                if str(item.get("object_id") or "").strip()
            ],
            "relevant_target_types": [
                str(item.get("object_type") or "").strip()
                for item in relevant_set
                if str(item.get("object_type") or "").strip()
            ],
            "candidate_source_counts": self._count_source_kinds(candidate_pool),
            "relevant_source_counts": self._count_source_kinds(relevant_set),
        }

    def _count_source_kinds(self, candidates: list[dict[str, Any]]) -> dict[str, int]:
        counts: dict[str, int] = {}
        for item in candidates:
            source_kind = str(item.get("source_kind") or item.get("source_power") or "unknown").strip() or "unknown"
            counts[source_kind] = counts.get(source_kind, 0) + 1
        return counts

    def _fallback_without_relevant_set(
        self,
        *,
        query: str,
        query_style: str,
        rewrite_query: bool,
        snapshot: dict[str, Any],
    ) -> ContextBindingResult:
        if query_style == "standalone":
            return self._build_fallback_result(
                fallback_type="retrieve_on_raw_query",
                reason="query_self_contained",
                candidates=[],
                confidence="medium",
                binding_snapshot=snapshot,
                rewritten_query=query if rewrite_query else None,
            )
        return self._build_fallback_result(
            fallback_type="needs_clarification",
            reason="no_relevant_targets",
            candidates=[],
            confidence="low",
            binding_snapshot=snapshot,
        )

    def _build_success_result(
        self,
        *,
        targets: tuple[dict[str, Any], ...],
        relevant_set: list[dict[str, Any]],
        resolved_target_ids: tuple[str, ...],
        confidence: str,
        strategy: str,
        rewritten_query: str | None,
        notes: tuple[str, ...],
        binding_snapshot: dict[str, Any],
    ) -> ContextBindingResult:
        metadata = self.response_helper.build_success_metadata(
            strategy=strategy,
            target=targets[-1] if targets else None,
            confidence=confidence,
        )
        snapshot = dict(binding_snapshot)
        snapshot["matched_by"] = metadata["matched_by"]
        snapshot["binding_confidence"] = confidence
        snapshot["resolved_target_count"] = len(resolved_target_ids)
        return ContextBindingResult(
            bound_targets=targets,
            binding_confidence=confidence,
            matched_by=metadata["matched_by"],
            clarification_hint=metadata["clarification_hint"],
            binding_summary=metadata["binding_summary"],
            notes=tuple(metadata["notes"]) + tuple(notes),
            rewritten_query=rewritten_query,
            relevant_set=tuple(dict(item) for item in relevant_set),
            resolved_target_ids=resolved_target_ids,
            binding_snapshot=snapshot,
        )

    def _build_fallback_result(
        self,
        *,
        fallback_type: str,
        reason: str,
        candidates: list[dict[str, Any]],
        confidence: str,
        binding_snapshot: dict[str, Any],
        rewritten_query: str | None = None,
    ) -> ContextBindingResult:
        metadata = self.response_helper.build_fallback_metadata(
            fallback_type=fallback_type,
            reason=reason,
            candidates=candidates,
            rewritten_query=rewritten_query,
        )
        needs_clarification = fallback_type == "needs_clarification"
        snapshot = dict(binding_snapshot)
        snapshot["matched_by"] = metadata["matched_by"]
        snapshot["fallback_type"] = fallback_type
        snapshot["fallback_reason"] = reason
        snapshot["candidate_target_ids"] = list(metadata["candidate_target_ids"])
        return ContextBindingResult(
            binding_confidence=confidence,
            binding_ambiguous=needs_clarification,
            matched_by=metadata["matched_by"],
            clarification_hint=metadata["clarification_hint"],
            binding_summary=metadata["binding_summary"],
            notes=tuple(metadata["notes"]),
            rewritten_query=rewritten_query,
            relevant_set=tuple(dict(item) for item in candidates),
            resolved_target_ids=(),
            needs_clarification=needs_clarification,
            fallback_type=fallback_type,
            reason=reason,
            binding_snapshot=snapshot,
        )
