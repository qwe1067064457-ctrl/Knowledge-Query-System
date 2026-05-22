from __future__ import annotations

from typing import Any


class PlanFormatHelper:
    def normalize_bundle(self, bundle: dict[str, Any]) -> dict[str, Any]:
        normalized = dict(bundle)
        ordered_steps = [dict(step) for step in normalized.get("ordered_steps", ())]
        deduped_steps: list[dict[str, Any]] = []
        seen_titles: set[str] = set()
        for index, step in enumerate(ordered_steps, start=1):
            title = str(step.get("title", "")).strip()
            if title in seen_titles:
                continue
            seen_titles.add(title)
            step.setdefault("sequence", index)
            deduped_steps.append(step)

        checkpoints = [dict(item) for item in normalized.get("execution_checkpoints", ())]
        deduped_checkpoints: list[dict[str, Any]] = []
        seen_checkpoint_ids: set[str] = set()
        for item in checkpoints:
            checkpoint_id = str(item.get("checkpoint_id", "")).strip()
            if checkpoint_id and checkpoint_id in seen_checkpoint_ids:
                continue
            if checkpoint_id:
                seen_checkpoint_ids.add(checkpoint_id)
            deduped_checkpoints.append(item)

        normalized["ordered_steps"] = deduped_steps
        normalized["execution_checkpoints"] = deduped_checkpoints
        normalized.setdefault(
            "plan_summary",
            {
                "planning_mode": normalized.get("planning_mode", "not_applicable"),
                "step_count": len(deduped_steps),
                "checkpoint_count": len(deduped_checkpoints),
                "comparison_unit_count": len(normalized.get("comparison_units", ())),
                "bound_target_ref_count": len(normalized.get("bound_target_refs", ())),
                "refined": bool(normalized.get("refined", False)),
                "fallback_used": bool(normalized.get("fallback_used", False)),
                "fallback_reason": list(normalized.get("fallback_reason", ())),
            },
        )
        normalized["format_helper_applied"] = True
        return normalized
