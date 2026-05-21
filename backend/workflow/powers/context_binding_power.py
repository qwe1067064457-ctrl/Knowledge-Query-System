from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class BindingResult:
    bound_targets: tuple[dict[str, Any], ...] = ()
    bound_evidence: tuple[dict[str, Any], ...] = ()
    comparison_set: tuple[dict[str, Any], ...] = ()
    binding_confidence: str = "low"
    binding_ambiguous: bool = False
    notes: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "bound_targets": [dict(item) for item in self.bound_targets],
            "bound_evidence": [dict(item) for item in self.bound_evidence],
            "comparison_set": [dict(item) for item in self.comparison_set],
            "binding_confidence": self.binding_confidence,
            "binding_ambiguous": self.binding_ambiguous,
            "notes": list(self.notes),
        }


class ContextBindingPower:
    _EXPLICIT_PATTERNS = (
        re.compile(r"(这个|那个|上面那个|你刚才说的)"),
        re.compile(r"(前两个|第二种|后一种)"),
    )

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
    ) -> BindingResult:
        if not candidates:
            return BindingResult(binding_confidence="low", binding_ambiguous=True, notes=("no_candidates",))

        explicit_hit = any(pattern.search(query) for pattern in self._EXPLICIT_PATTERNS)
        if explicit_hit:
            target = candidates[-1]
            return BindingResult(
                bound_targets=(target,),
                binding_confidence="high",
                notes=("explicit_pattern",),
            )

        if len(query.strip()) <= 20 and recent_power:
            for candidate in reversed(candidates):
                if recent_object_type and candidate.get("object_type") != recent_object_type:
                    continue
                if candidate.get("source_power") == recent_power:
                    return BindingResult(
                        bound_targets=(candidate,),
                        binding_confidence="medium",
                        notes=("topic_continuity",),
                    )

        return BindingResult(binding_confidence="low", binding_ambiguous=True, notes=("binding_ambiguous",))
