from __future__ import annotations

import re
from typing import Any

from workflow.helpers.binding_response_helper import BindingResponseHelper
from workflow.types import ContextBindingResult


class ContextBindingPower:
    _EXPLICIT_PATTERNS = (
        re.compile(r"(这个|那个|上面那个|你刚才说的)"),
        re.compile(r"(前两个|第二种|后一种)"),
    )

    def __init__(self, response_helper: BindingResponseHelper | None = None) -> None:
        self.response_helper = response_helper or BindingResponseHelper()

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
        recent_power: str | None = None,
        recent_object_type: str | None = None,
    ) -> ContextBindingResult:
        if not candidates:
            metadata = self.response_helper.build_ambiguity_metadata(
                query=query,
                reason="no_candidates",
                candidates=[],
            )
            return ContextBindingResult(
                binding_confidence="low",
                binding_ambiguous=True,
                matched_by=metadata["matched_by"],
                clarification_hint=metadata["clarification_hint"],
                binding_summary=metadata["binding_summary"],
                notes=tuple(metadata["notes"]),
            )

        explicit_hit = any(pattern.search(query) for pattern in self._EXPLICIT_PATTERNS)
        if explicit_hit:
            target = self._select_primary_target(candidates)
            metadata = self.response_helper.build_success_metadata(
                strategy="explicit_pattern",
                target=target,
                confidence="high",
            )
            return ContextBindingResult(
                bound_targets=(target,),
                binding_confidence="high",
                matched_by=metadata["matched_by"],
                clarification_hint=metadata["clarification_hint"],
                binding_summary=metadata["binding_summary"],
                notes=tuple(metadata["notes"]),
            )

        if len(query.strip()) <= 20 and recent_power:
            for candidate in reversed(candidates):
                if recent_object_type and candidate.get("object_type") != recent_object_type:
                    continue
                if candidate.get("source_power") == recent_power:
                    metadata = self.response_helper.build_success_metadata(
                        strategy="topic_continuity",
                        target=candidate,
                        confidence="medium",
                    )
                    return ContextBindingResult(
                        bound_targets=(candidate,),
                        binding_confidence="medium",
                        matched_by=metadata["matched_by"],
                        clarification_hint=metadata["clarification_hint"],
                        binding_summary=metadata["binding_summary"],
                        notes=tuple(metadata["notes"]),
                    )

        metadata = self.response_helper.build_ambiguity_metadata(
            query=query,
            reason="binding_ambiguous",
            candidates=candidates,
        )
        return ContextBindingResult(
            binding_confidence="low",
            binding_ambiguous=True,
            matched_by=metadata["matched_by"],
            clarification_hint=metadata["clarification_hint"],
            binding_summary=metadata["binding_summary"],
            notes=tuple(metadata["notes"]),
        )

    def _select_primary_target(self, candidates: list[dict[str, Any]]) -> dict[str, Any]:
        for candidate in reversed(candidates):
            if candidate.get("object_type") not in {"evidence_ref", "retrieval_result_ref"}:
                return candidate
        return candidates[-1]
