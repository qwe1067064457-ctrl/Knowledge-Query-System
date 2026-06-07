from __future__ import annotations

from workflow.types import EvidenceAssessmentResult


def summarize_challenge_findings(
    *,
    targets: list[dict],
    evidence_assessment: EvidenceAssessmentResult,
) -> tuple[dict, ...]:
    supporting_refs = list(evidence_assessment.supporting_evidence_refs)
    findings = []
    for index, target in enumerate(targets, start=1):
        target_ref = target.get("object_id") or target.get("content") or f"target_{index}"
        matched_refs = evidence_assessment.matched_evidence_refs_for(str(target_ref))
        if evidence_assessment.target_is_matched(str(target_ref)):
            judgment = "supported"
            reason = "Coarse evidence coverage indicates the current challenge target is supported by retrieved evidence."
        else:
            judgment = "insufficient_evidence"
            reason = "Coarse evidence coverage indicates the current challenge target still lacks enough supporting evidence."
        findings.append(
            {
                "target_ref": target_ref,
                "judgment": judgment,
                "reason": reason,
                "supporting_evidence_refs": matched_refs or supporting_refs,
            }
        )
    return tuple(findings)


def build_challenge_answer_constraints(
    *,
    evidence_assessment: EvidenceAssessmentResult,
    sufficient: bool,
) -> dict:
    return {
        "must_cite_sources": True,
        "must_acknowledge_uncertainty": not sufficient,
        "source_type_quality_band": evidence_assessment.source_type_quality_band,
        "channel_quality_band": evidence_assessment.channel_quality_band,
    }
