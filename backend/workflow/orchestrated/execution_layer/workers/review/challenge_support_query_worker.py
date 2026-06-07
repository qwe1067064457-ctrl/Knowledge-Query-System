from __future__ import annotations

from typing import Any

from workflow.types import QueryUnit

from workflow.orchestrated.execution_layer.workers.base import BaseWorker


class ChallengeSupportQueryWorker(BaseWorker):
    name = "challenge_support_query"
    description = "Build support query units for challenge follow-up retrieval."

    def run(
        self,
        query: str,
        targets: list[dict[str, Any]] | tuple[dict[str, Any], ...],
        requested_target_refs: list[str] | tuple[str, ...] = (),
    ):
        requested = {str(ref) for ref in requested_target_refs if ref}
        units: list[dict[str, Any]] = []
        for index, target in enumerate(targets, start=1):
            target_id = str(target.get("object_id") or target.get("content") or f"target_{index}")
            target_refs = tuple(str(ref) for ref in target.get("refs", ()) if ref)
            candidate_refs = {target_id, *target_refs}
            if requested and requested.isdisjoint(candidate_refs):
                continue
            target_text = self._target_support_text(dict(target), fallback=target_id)
            normalized_target_refs = target_refs or (target_id,)
            support_text = f"{query} {target_text}".strip()
            units.append(
                QueryUnit(
                    unit_id=f"challenge_support_{index}",
                    text=support_text,
                    origin="support",
                    target_refs=normalized_target_refs,
                ).to_dict()
            )
        return {"query_units": units}

    def _target_support_text(self, target: dict[str, Any], *, fallback: str) -> str:
        structured = target.get("structured_payload")
        if isinstance(structured, dict):
            disputed_span = str(structured.get("disputed_span") or "").strip()
            if disputed_span:
                return disputed_span
        return str(target.get("content") or fallback).strip()
