from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class AnswerAssemblyFinding:
    unit_id: str
    role: str
    summary: str
    confidence: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "unit_id": self.unit_id,
            "role": self.role,
            "summary": self.summary,
        }
        if self.confidence:
            payload["confidence"] = self.confidence
        return payload


@dataclass(frozen=True)
class EvidenceAnchor:
    source_ref: str
    supports: str

    def to_dict(self) -> dict[str, str]:
        return {"source_ref": self.source_ref, "supports": self.supports}


@dataclass(frozen=True)
class AnswerAssemblyPackage:
    question: str
    execution_summary: dict[str, Any] = field(default_factory=dict)
    main_findings: tuple[AnswerAssemblyFinding, ...] = ()
    primary_findings: tuple[AnswerAssemblyFinding, ...] = ()
    supporting_findings: tuple[AnswerAssemblyFinding, ...] = ()
    status_findings: tuple[AnswerAssemblyFinding, ...] = ()
    evidence_anchors: tuple[EvidenceAnchor, ...] = ()
    answer_cautions: tuple[str, ...] = ()
    route_constraints: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "question": self.question,
            "execution_summary": dict(self.execution_summary),
            "main_findings": [item.to_dict() for item in self.main_findings],
            "primary_findings": [item.to_dict() for item in self.primary_findings],
            "supporting_findings": [item.to_dict() for item in self.supporting_findings],
            "status_findings": [item.to_dict() for item in self.status_findings],
            "evidence_anchors": [item.to_dict() for item in self.evidence_anchors],
            "answer_cautions": list(self.answer_cautions),
            "route_constraints": dict(self.route_constraints),
        }
