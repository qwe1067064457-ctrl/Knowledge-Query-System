from __future__ import annotations

from intent.schema.evidence_types import EvidenceQualityReport, TypedEvidence
from intent.schema.intent_types import IntentInput


def build_adjudication_prompt(
    *,
    intent_input: IntentInput,
    typed_evidence: tuple[TypedEvidence, ...],
    quality_report: EvidenceQualityReport,
) -> dict[str, object]:
    """Build a structured adjudication payload instead of a free-form prompt."""

    return {
        "task": "adjudicate_intent_evidence",
        "instruction": (
            "Judge only the supplied evidence. Do not redo full intent classification "
            "from scratch; correct, accept, or reject evidence needed by resolver."
        ),
        "input": intent_input.to_dict(),
        "typed_evidence": [item.to_dict() for item in typed_evidence],
        "quality_report": quality_report.to_dict(),
    }

