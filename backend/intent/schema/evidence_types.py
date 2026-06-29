from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Literal


EvidenceSource = Literal[
    "surface_trigger",
    "small_model",
    "context_state",
    "retrieval_trace",
    "human",
    "llm_adjudication",
]
CaseLevelOutcome = Literal[
    "auto_resolve",
    "auto_resolve_with_warnings",
    "blocked_by_missing_prerequisite",
    "requires_adjudication",
    "guard_required",
]
EvidenceSignalStatus = Literal[
    "accepted",
    "downgraded",
    "rejected",
]
SignalCriticality = Literal[
    "route",
    "task_shape",
    "context_dependency",
    "safety",
    "modifier",
    "diagnostic",
]
CalibrationQuality = Literal["good", "weak", "unknown"]


@dataclass(frozen=True)
class TypedEvidence:
    """A typed signal used after surface detection and before final routing."""

    signal: str
    value: Any
    source: EvidenceSource
    score: float | None
    threshold: float | None
    margin: float | None
    calibration_quality: CalibrationQuality
    prerequisites: tuple[str, ...]
    missing_prerequisites: tuple[str, ...]
    criticality: SignalCriticality
    rationale: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "signal": self.signal,
            "value": self.value,
            "source": self.source,
            "score": self.score,
            "threshold": self.threshold,
            "margin": self.margin,
            "calibration_quality": self.calibration_quality,
            "prerequisites": list(self.prerequisites),
            "missing_prerequisites": list(self.missing_prerequisites),
            "criticality": self.criticality,
            "rationale": self.rationale,
        }


@dataclass(frozen=True)
class EvidenceQualityReport:
    """Quality-gate output: signal quality plus case-level convergence state."""

    accepted_evidence: tuple[TypedEvidence, ...]
    downgraded_evidence: tuple[TypedEvidence, ...]
    rejected_evidence: tuple[TypedEvidence, ...]
    conflicts: tuple[str, ...]
    ambiguities: tuple[str, ...]
    missing_prerequisites: tuple[str, ...]
    case_level: CaseLevelOutcome
    case_reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "accepted_evidence": [item.to_dict() for item in self.accepted_evidence],
            "downgraded_evidence": [item.to_dict() for item in self.downgraded_evidence],
            "rejected_evidence": [item.to_dict() for item in self.rejected_evidence],
            "conflicts": list(self.conflicts),
            "ambiguities": list(self.ambiguities),
            "missing_prerequisites": list(self.missing_prerequisites),
            "case_level": self.case_level,
            "case_reason": self.case_reason,
        }


@dataclass(frozen=True)
class AdjudicationResult:
    """Structured LLM adjudication result; it does not replace resolver."""

    accepted_evidence: tuple[TypedEvidence, ...]
    corrected_evidence: tuple[TypedEvidence, ...]
    rejected_evidence: tuple[TypedEvidence, ...]
    clarified_ambiguity_type: str
    fallback_recommendation: CaseLevelOutcome
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "accepted_evidence": [item.to_dict() for item in self.accepted_evidence],
            "corrected_evidence": [item.to_dict() for item in self.corrected_evidence],
            "rejected_evidence": [item.to_dict() for item in self.rejected_evidence],
            "clarified_ambiguity_type": self.clarified_ambiguity_type,
            "fallback_recommendation": self.fallback_recommendation,
            "reason": self.reason,
        }

