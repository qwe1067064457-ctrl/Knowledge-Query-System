from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class VerifyResultPayload:
    judgment: str = "pending_verification"
    can_proceed: bool = True
    confidence: str = "medium"
    summary: str = ""
    key_reasons: tuple[str, ...] = ()
    consumed_working_memory: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "judgment": self.judgment,
            "can_proceed": self.can_proceed,
            "confidence": self.confidence,
            "summary": self.summary,
            "key_reasons": list(self.key_reasons),
            "consumed_working_memory": list(self.consumed_working_memory),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any] | None) -> "VerifyResultPayload":
        data = dict(payload or {})
        return cls(
            judgment=str(data.get("judgment", "pending_verification")),
            can_proceed=bool(data.get("can_proceed", True)),
            confidence=str(data.get("confidence", "medium")),
            summary=str(data.get("summary", "")),
            key_reasons=tuple(str(item) for item in data.get("key_reasons", ()) or () if item),
            consumed_working_memory=tuple(
                str(item) for item in data.get("consumed_working_memory", ()) or () if item
            ),
        )


@dataclass(frozen=True)
class CompareResultPayload:
    comparison_status: str = "comparison_pending"
    summary: str = ""
    dimensions: tuple[str, ...] = ()
    tradeoff: tuple[str, ...] = ()
    confidence: str = "medium"
    consumed_working_memory: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "comparison_status": self.comparison_status,
            "summary": self.summary,
            "dimensions": list(self.dimensions),
            "tradeoff": list(self.tradeoff),
            "confidence": self.confidence,
            "consumed_working_memory": list(self.consumed_working_memory),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any] | None) -> "CompareResultPayload":
        data = dict(payload or {})
        return cls(
            comparison_status=str(data.get("comparison_status", "comparison_pending")),
            summary=str(data.get("summary", "")),
            dimensions=tuple(str(item) for item in data.get("dimensions", ()) or () if item),
            tradeoff=tuple(str(item) for item in data.get("tradeoff", ()) or () if item),
            confidence=str(data.get("confidence", "medium")),
            consumed_working_memory=tuple(
                str(item) for item in data.get("consumed_working_memory", ()) or () if item
            ),
        )


@dataclass(frozen=True)
class SynthesisResultPayload:
    main_conclusion: str = ""
    supporting_points: tuple[str, ...] = ()
    cautions: tuple[str, ...] = ()
    final_text_draft: str = ""
    confidence: str = "medium"
    consumed_working_memory: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "main_conclusion": self.main_conclusion,
            "supporting_points": list(self.supporting_points),
            "cautions": list(self.cautions),
            "final_text_draft": self.final_text_draft,
            "confidence": self.confidence,
            "consumed_working_memory": list(self.consumed_working_memory),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any] | None) -> "SynthesisResultPayload":
        data = dict(payload or {})
        return cls(
            main_conclusion=str(data.get("main_conclusion", "")),
            supporting_points=tuple(str(item) for item in data.get("supporting_points", ()) or () if item),
            cautions=tuple(str(item) for item in data.get("cautions", ()) or () if item),
            final_text_draft=str(data.get("final_text_draft", "")),
            confidence=str(data.get("confidence", "medium")),
            consumed_working_memory=tuple(
                str(item) for item in data.get("consumed_working_memory", ()) or () if item
            ),
        )


def normalize_result_payload(*, capability: str, payload: dict[str, Any] | None) -> dict[str, Any]:
    if capability == "verify":
        return VerifyResultPayload.from_dict(payload).to_dict()
    if capability == "compare":
        return CompareResultPayload.from_dict(payload).to_dict()
    if capability == "synthesis":
        return SynthesisResultPayload.from_dict(payload).to_dict()
    return dict(payload or {})


__all__ = [
    "CompareResultPayload",
    "SynthesisResultPayload",
    "VerifyResultPayload",
    "normalize_result_payload",
]
