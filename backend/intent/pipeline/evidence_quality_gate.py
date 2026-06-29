from __future__ import annotations

from intent.schema.evidence_types import CaseLevelOutcome, EvidenceQualityReport, TypedEvidence


CRITICALITIES = {"route", "task_shape", "context_dependency", "safety"}
HARD_GUARD_SIGNALS = {"unsupported", "out_of_scope"}


def evaluate_evidence_quality(evidence: tuple[TypedEvidence, ...]) -> EvidenceQualityReport:
    """Decide whether structured evidence can converge without LLM help."""

    accepted: list[TypedEvidence] = []
    downgraded: list[TypedEvidence] = []
    rejected: list[TypedEvidence] = []
    for item in evidence:
        if _is_rejected(item):
            rejected.append(item)
        elif _is_accepted(item):
            accepted.append(item)
        else:
            downgraded.append(item)

    conflicts = _detect_conflicts(tuple(accepted), tuple(downgraded))
    missing_prerequisites = _collect_missing_prerequisites(tuple(accepted), tuple(downgraded))
    ambiguities = _detect_ambiguities(tuple(accepted), tuple(downgraded), conflicts)
    case_level, reason = _decide(
        accepted=tuple(accepted),
        downgraded=tuple(downgraded),
        rejected=tuple(rejected),
        conflicts=conflicts,
        ambiguities=ambiguities,
        missing_prerequisites=missing_prerequisites,
    )
    return EvidenceQualityReport(
        accepted_evidence=tuple(accepted),
        downgraded_evidence=tuple(downgraded),
        rejected_evidence=tuple(rejected),
        conflicts=conflicts,
        ambiguities=ambiguities,
        missing_prerequisites=missing_prerequisites,
        case_level=case_level,
        case_reason=reason,
    )


def _is_rejected(item: TypedEvidence) -> bool:
    if item.score is None or item.threshold is None:
        return False
    return item.score < item.threshold and item.criticality in CRITICALITIES


def _is_accepted(item: TypedEvidence) -> bool:
    if item.criticality == "safety" and item.signal in HARD_GUARD_SIGNALS:
        return (item.score or 0.0) >= 0.85 and not item.missing_prerequisites
    if item.source in {"context_state", "human", "llm_adjudication"}:
        return not item.missing_prerequisites
    if item.source == "small_model":
        return (
            item.calibration_quality == "good"
            and (item.margin is not None and item.margin >= 0.15)
            and not item.missing_prerequisites
        )
    if item.source == "surface_trigger":
        return (
            item.score is not None
            and item.score >= 0.85
            and (item.margin is not None and item.margin >= 0.0)
            and not item.missing_prerequisites
        )
    return False


def _detect_conflicts(
    accepted: tuple[TypedEvidence, ...],
    downgraded: tuple[TypedEvidence, ...],
) -> tuple[str, ...]:
    conflicts: list[str] = []
    route_values = {
        str(item.value)
        for item in accepted
        if item.signal == "main_intent" and item.value
    }
    if len(route_values) >= 2:
        conflicts.append("accepted_route_conflict:" + ",".join(sorted(route_values)))

    for signal in ("task_complexity", "task_shape", "task_topology"):
        values = {
            str(item.value)
            for item in accepted
            if item.signal == signal and item.value
        }
        if len(values) >= 2:
            conflicts.append(f"accepted_{signal}_conflict:" + ",".join(sorted(values)))

    if _has_signal((*accepted, *downgraded), "clarify_hint") and (
        _has_signal((*accepted, *downgraded), "challenge")
        or _has_signal((*accepted, *downgraded), "follow_up")
    ):
        conflicts.append("context_resolution_conflict")
    return tuple(conflicts)


def _collect_missing_prerequisites(
    accepted: tuple[TypedEvidence, ...],
    downgraded: tuple[TypedEvidence, ...],
) -> tuple[str, ...]:
    missing: list[str] = []
    for item in (*accepted, *downgraded):
        for prerequisite in item.missing_prerequisites:
            if prerequisite not in missing:
                missing.append(prerequisite)
    return tuple(missing)


def _detect_ambiguities(
    accepted: tuple[TypedEvidence, ...],
    downgraded: tuple[TypedEvidence, ...],
    conflicts: tuple[str, ...],
) -> tuple[str, ...]:
    ambiguities = list(conflicts)
    for item in (*accepted, *downgraded):
        if _is_uncertain_critical_model_signal(item):
            label = f"uncertain_{item.criticality}:{item.signal}"
            if label not in ambiguities:
                ambiguities.append(label)
    return tuple(ambiguities)


def _decide(
    *,
    accepted: tuple[TypedEvidence, ...],
    downgraded: tuple[TypedEvidence, ...],
    rejected: tuple[TypedEvidence, ...],
    conflicts: tuple[str, ...],
    ambiguities: tuple[str, ...],
    missing_prerequisites: tuple[str, ...],
) -> tuple[CaseLevelOutcome, str]:
    if any(item.criticality == "safety" and item.signal in HARD_GUARD_SIGNALS for item in accepted):
        return "guard_required", "accepted safety evidence requires guard handling"
    if missing_prerequisites and _has_critical_missing_prerequisite(accepted, downgraded):
        return "blocked_by_missing_prerequisite", "trusted evidence is missing required context"
    if conflicts:
        return "requires_adjudication", "trusted critical evidence has conflicts"
    if (
        not _has_adjudicated_critical_signal(accepted)
        and any(_is_uncertain_critical_model_signal(item) for item in (*accepted, *downgraded, *rejected))
    ):
        return "requires_adjudication", "critical model evidence is weak or close to threshold"
    if _has_unstable_critical_signal(accepted, downgraded, rejected):
        return "requires_adjudication", "critical evidence has no stable accepted signal"
    if any(item.criticality not in CRITICALITIES for item in downgraded):
        return "auto_resolve_with_warnings", "non-blocking evidence was downgraded"
    if downgraded:
        return "auto_resolve_with_warnings", "critical path converged with downgraded trace evidence"
    return "auto_resolve", "evidence can converge without escalation"


def _is_uncertain_critical_model_signal(item: TypedEvidence) -> bool:
    if item.source != "small_model" or item.criticality not in CRITICALITIES:
        return False
    if item.calibration_quality == "weak":
        return True
    return item.margin is not None and item.margin < 0.1


def _has_critical_missing_prerequisite(
    accepted: tuple[TypedEvidence, ...],
    downgraded: tuple[TypedEvidence, ...],
) -> bool:
    return any(
        item.missing_prerequisites and item.criticality in {"context_dependency", "modifier"}
        for item in (*accepted, *downgraded)
    )


def _has_unstable_critical_signal(
    accepted: tuple[TypedEvidence, ...],
    downgraded: tuple[TypedEvidence, ...],
    rejected: tuple[TypedEvidence, ...],
) -> bool:
    """Detect an explicit route signal that never produced a stable accepted value."""

    has_route_signal = any(
        item.criticality == "route"
        for item in (*accepted, *downgraded, *rejected)
    )
    has_accepted_route = any(item.criticality == "route" for item in accepted)
    return has_route_signal and not has_accepted_route


def _has_adjudicated_critical_signal(accepted: tuple[TypedEvidence, ...]) -> bool:
    return any(
        item.source == "llm_adjudication" and item.criticality in CRITICALITIES
        for item in accepted
    )


def _has_signal(evidence: tuple[TypedEvidence, ...], signal: str) -> bool:
    return any(item.signal == signal and item.value for item in evidence)

