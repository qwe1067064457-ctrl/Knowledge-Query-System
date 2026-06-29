from __future__ import annotations

from intent.pipeline.evidence_quality_gate import evaluate_evidence_quality
from intent.schema.evidence_types import TypedEvidence


def _evidence(
    *,
    signal: str = "main_intent",
    value=True,
    source="small_model",
    score: float = 0.9,
    threshold: float = 0.6,
    calibration_quality="good",
    criticality="route",
    missing_prerequisites: tuple[str, ...] = (),
) -> TypedEvidence:
    return TypedEvidence(
        signal=signal,
        value=value,
        source=source,
        score=score,
        threshold=threshold,
        margin=round(score - threshold, 4),
        calibration_quality=calibration_quality,
        prerequisites=missing_prerequisites,
        missing_prerequisites=missing_prerequisites,
        criticality=criticality,
        rationale="test",
    )


def test_high_margin_model_route_signal_is_accepted() -> None:
    report = evaluate_evidence_quality(
        (_evidence(value="qa", score=0.92, calibration_quality="good"),)
    )

    assert report.case_level == "auto_resolve"
    assert [item.value for item in report.accepted_evidence] == ["qa"]


def test_low_margin_weak_model_route_signal_requires_adjudication() -> None:
    report = evaluate_evidence_quality(
        (_evidence(value="qa", score=0.62, calibration_quality="weak"),)
    )

    assert report.case_level == "requires_adjudication"
    assert "uncertain_route:main_intent" in report.ambiguities


def test_follow_up_with_missing_history_blocks_by_prerequisite() -> None:
    report = evaluate_evidence_quality(
        (
            _evidence(
                signal="follow_up",
                source="context_state",
                score=0.9,
                threshold=0.75,
                criticality="modifier",
                missing_prerequisites=("history",),
            ),
        )
    )

    assert report.case_level == "blocked_by_missing_prerequisite"
    assert report.missing_prerequisites == ("history",)


def test_weak_modifier_is_downgraded_without_blocking_route() -> None:
    report = evaluate_evidence_quality(
        (
            _evidence(value="qa", score=0.91, calibration_quality="good"),
            _evidence(
                signal="soft_doubt",
                source="surface_trigger",
                score=0.3,
                threshold=0.6,
                calibration_quality="unknown",
                criticality="modifier",
            ),
        )
    )

    assert report.case_level == "auto_resolve_with_warnings"
    assert [item.signal for item in report.downgraded_evidence] == ["soft_doubt"]


def test_unsupported_guard_overrides_other_evidence() -> None:
    report = evaluate_evidence_quality(
        (
            _evidence(signal="out_of_scope", source="surface_trigger", score=0.9, threshold=0.85, criticality="safety"),
            _evidence(value="qa", score=0.95, calibration_quality="good"),
        )
    )

    assert report.case_level == "guard_required"


def test_strong_route_conflict_requires_adjudication() -> None:
    report = evaluate_evidence_quality(
        (
            _evidence(value="qa", source="surface_trigger", score=0.9, threshold=0.85, calibration_quality="unknown"),
            _evidence(value="chat", source="small_model", score=0.92, threshold=0.6, calibration_quality="good"),
        )
    )

    assert report.case_level == "requires_adjudication"
    assert report.conflicts == ("accepted_route_conflict:chat,qa",)
