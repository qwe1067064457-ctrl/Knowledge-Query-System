from __future__ import annotations

from typing import Any


class BindingResponseHelper:
    def build_success_metadata(
        self,
        *,
        strategy: str,
        target: dict[str, Any] | None,
        confidence: str,
    ) -> dict[str, Any]:
        target_label = str((target or {}).get("content") or (target or {}).get("object_id") or "").strip()
        note = strategy
        if target_label:
            note = f"{strategy}:{target_label}"
        return {
            "matched_by": strategy,
            "notes": (note,),
            "clarification_hint": None,
            "binding_summary": (
                f"Bound the current request via {strategy} with {confidence} confidence."
                if target_label
                else f"Bound the current request via {strategy}."
            ),
        }

    def build_ambiguity_metadata(
        self,
        *,
        query: str,
        reason: str,
        candidates: list[dict[str, Any]],
    ) -> dict[str, Any]:
        candidate_labels = [
            str(item.get("content") or item.get("object_id") or item.get("object_type") or "").strip()
            for item in candidates[:3]
        ]
        candidate_labels = [label for label in candidate_labels if label]
        if candidate_labels:
            clarification_hint = (
                f"当前请求可能指向这些对象之一：{', '.join(candidate_labels)}。请明确你指的是哪一个。"
            )
        else:
            clarification_hint = "当前请求依赖前文对象，但还无法稳定定位，请补充具体对象。"
        return {
            "matched_by": "ambiguity_fallback",
            "notes": (reason,),
            "clarification_hint": clarification_hint,
            "binding_summary": f"Could not bind the request safely because {reason}.",
            "query_excerpt": query[:80],
        }

    def build_fallback_metadata(
        self,
        *,
        fallback_type: str,
        reason: str,
        candidates: list[dict[str, Any]],
        rewritten_query: str | None = None,
    ) -> dict[str, Any]:
        candidate_ids = [
            str(item.get("object_id") or item.get("entry_id") or item.get("content") or "").strip()
            for item in candidates[:5]
            if str(item.get("object_id") or item.get("entry_id") or item.get("content") or "").strip()
        ]
        clarification_hint = None
        if fallback_type == "needs_clarification":
            if candidate_ids:
                clarification_hint = f"当前请求可能在这些对象之间存在歧义：{', '.join(candidate_ids)}。请明确指的是哪一个。"
            else:
                clarification_hint = "当前请求依赖前文对象，但还无法稳定定位，请补充更具体的对象。"
        return {
            "matched_by": "fallback",
            "notes": (f"{fallback_type}:{reason}",),
            "clarification_hint": clarification_hint,
            "binding_summary": f"Context binding fell back to {fallback_type} because {reason}.",
            "fallback_type": fallback_type,
            "reason": reason,
            "candidate_target_ids": candidate_ids,
            "rewritten_query": rewritten_query,
        }
