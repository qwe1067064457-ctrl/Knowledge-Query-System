from __future__ import annotations

from intent import classify_intent


def test_surface_trigger_match_becomes_surface_trigger_evidence() -> None:
    result = classify_intent("劳动合同法中试用期最长多久？")

    qa_evidence = [
        item
        for item in result.evidence.typed_evidence
        if item.signal == "qa" and item.rationale.startswith("surface_trigger:")
    ]

    assert qa_evidence
    assert {item.source for item in qa_evidence} == {"surface_trigger"}


def test_missing_context_challenge_is_not_high_trust_challenge_evidence() -> None:
    result = classify_intent("你确定吗？")

    accepted_signals = {
        item.signal for item in (result.evidence.quality_report.accepted_evidence if result.evidence.quality_report else ())
    }
    missing = result.evidence.quality_report.missing_prerequisites if result.evidence.quality_report else ()

    assert "challenge" not in accepted_signals
    assert "previous_answer" in missing
    assert result.evidence.quality_report is not None
    assert result.evidence.quality_report.case_level == "blocked_by_missing_prerequisite"
