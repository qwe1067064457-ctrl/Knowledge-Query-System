from __future__ import annotations

from typing import Any


LABEL_TO_SCORE = {"good": 1.0, "weak": 0.5, "bad": 0.0}
WEIGHTS = {
    "continuity_support": 0.30,
    "key_state_capture": 0.25,
    "noise_control": 0.15,
    "freshness": 0.10,
    "handoff_utility": 0.20,
}
ALLOWED_LABELS = set(LABEL_TO_SCORE)


def grade_working_memory_case(
    case: dict[str, Any],
    *,
    semantic_labels: dict[str, str] | None = None,
) -> dict[str, Any]:
    semantic_labels = semantic_labels or {}
    summary = dict(case.get("working_memory_summary") or {})
    entries = list(summary.get("entries") or [])
    head = dict(summary.get("head") or {})
    entry_types = {str(item.get("entry_type") or "") for item in entries if isinstance(item, dict)}
    noise_count = int(summary.get("noise_entry_count", 0) or 0)
    stale_count = int(summary.get("stale_entry_count", 0) or 0)

    dimension_labels = {
        "continuity_support": _pick_label(
            "continuity_support",
            semantic_labels,
            fallback=_continuity_label(case, entry_types),
        ),
        "key_state_capture": _pick_label(
            "key_state_capture",
            semantic_labels,
            fallback=_key_state_label(case, entry_types),
        ),
        "noise_control": _pick_label(
            "noise_control",
            semantic_labels,
            fallback=_noise_label(noise_count),
        ),
        "freshness": _pick_label(
            "freshness",
            semantic_labels,
            fallback=_freshness_label(stale_count),
        ),
        "handoff_utility": _pick_label(
            "handoff_utility",
            semantic_labels,
            fallback=_handoff_label(case, entry_types, head, noise_count, stale_count),
        ),
    }
    dimension_scores = {key: LABEL_TO_SCORE[label] for key, label in dimension_labels.items()}
    raw_score = sum(WEIGHTS[key] * dimension_scores[key] for key in WEIGHTS)
    capped_label = _label_for_score(raw_score)
    hard_cap = None
    if case.get("expected_handoff_ready") and dimension_labels["handoff_utility"] == "bad":
        capped_label = "bad"
        hard_cap = "handoff_not_ready"

    reasons: list[str] = []
    if case.get("expected_focus_task_present") and "focus_task" not in entry_types:
        reasons.append("missing_focus_task")
    if case.get("expected_resolved_query_present") and "resolved_query" not in entry_types:
        reasons.append("missing_resolved_query")
    if case.get("expected_review_outcome_present") and "review_outcome" not in entry_types:
        reasons.append("missing_review_outcome")
    if dimension_labels["noise_control"] == "bad":
        reasons.append("too_noisy")
    if dimension_labels["freshness"] == "bad":
        reasons.append("too_stale")
    if dimension_labels["handoff_utility"] == "bad":
        reasons.append("handoff_not_ready")

    return {
        "dimension_labels": dimension_labels,
        "dimension_scores": dimension_scores,
        "weights": dict(WEIGHTS),
        "score": round(raw_score, 4),
        "label": capped_label,
        "reasons": reasons,
        "metadata": {
            "hard_cap": hard_cap,
            "heuristic_labels": {key: key not in semantic_labels for key in WEIGHTS},
            "working_memory_summary": summary,
        },
    }


def _continuity_label(case: dict[str, Any], entry_types: set[str]) -> str:
    required: list[str] = []
    if case.get("expected_focus_task_present"):
        required.append("focus_task")
    if case.get("expected_resolved_query_present"):
        required.append("resolved_query")
    missing = [item for item in required if item not in entry_types]
    if not missing:
        return "good"
    if len(missing) < len(required):
        return "weak"
    return "bad"


def _key_state_label(case: dict[str, Any], entry_types: set[str]) -> str:
    required = 0
    present = 0
    checks = [
        ("focus_task", case.get("expected_focus_task_present")),
        ("resolved_query", case.get("expected_resolved_query_present")),
        ("review_outcome", case.get("expected_review_outcome_present")),
    ]
    for key, needed in checks:
        if needed:
            required += 1
            if key in entry_types:
                present += 1
    if required == 0:
        return "weak"
    if present == required:
        return "good"
    if present > 0:
        return "weak"
    return "bad"


def _noise_label(noise_count: int) -> str:
    if noise_count <= 0:
        return "good"
    if noise_count == 1:
        return "weak"
    return "bad"


def _freshness_label(stale_count: int) -> str:
    if stale_count <= 0:
        return "good"
    if stale_count == 1:
        return "weak"
    return "bad"


def _handoff_label(
    case: dict[str, Any],
    entry_types: set[str],
    head: dict[str, Any],
    noise_count: int,
    stale_count: int,
) -> str:
    if not case.get("expected_handoff_ready"):
        return "weak"
    if not head.get("active_entry_ids"):
        return "bad"
    if case.get("expected_focus_task_present") and "focus_task" not in entry_types:
        return "bad"
    if case.get("expected_resolved_query_present") and "resolved_query" not in entry_types:
        return "bad"
    if noise_count > 1 or stale_count > 1:
        return "bad"
    if noise_count == 1 or stale_count == 1:
        return "weak"
    return "good"


def _pick_label(name: str, labels: dict[str, str], *, fallback: str) -> str:
    label = labels.get(name, fallback)
    if label not in ALLOWED_LABELS:
        raise ValueError(f"Unsupported working memory label for {name}: {label}")
    return label


def _label_for_score(score: float) -> str:
    if score >= 0.80:
        return "good"
    if score >= 0.45:
        return "weak"
    return "bad"
