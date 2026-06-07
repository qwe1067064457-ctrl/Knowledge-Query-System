from __future__ import annotations

from typing import Any


LABEL_TO_SCORE = {"good": 1.0, "weak": 0.5, "bad": 0.0}
WEIGHTS = {
    "should_write": 0.25,
    "should_not_write": 0.20,
    "type_correctness": 0.20,
    "scope_correctness": 0.20,
    "anchor_preservation": 0.15,
}
ALLOWED_LABELS = set(LABEL_TO_SCORE)


def grade_long_term_memory_case(
    case: dict[str, Any],
    *,
    semantic_labels: dict[str, str] | None = None,
) -> dict[str, Any]:
    semantic_labels = semantic_labels or {}
    persist_summary = dict(case.get("persist_summary") or {})
    expected_write = bool(case.get("expected_write"))
    actual_write = bool(persist_summary.get("persisted"))
    actual_type = str(persist_summary.get("memory_type") or "")
    actual_scope = str(persist_summary.get("scope") or "")
    anchor_after = case.get("anchor_after")

    dimension_labels = {
        "should_write": _pick_label(
            "should_write",
            semantic_labels,
            fallback=_should_write_label(expected_write=expected_write, actual_write=actual_write),
        ),
        "should_not_write": _pick_label(
            "should_not_write",
            semantic_labels,
            fallback=_should_not_write_label(expected_write=expected_write, actual_write=actual_write),
        ),
        "type_correctness": _pick_label(
            "type_correctness",
            semantic_labels,
            fallback=_type_label(expected_type=case.get("expected_memory_type"), actual_type=actual_type, actual_write=actual_write),
        ),
        "scope_correctness": _pick_label(
            "scope_correctness",
            semantic_labels,
            fallback=_scope_label(expected_scope=case.get("expected_scope"), actual_scope=actual_scope, actual_write=actual_write),
        ),
        "anchor_preservation": _pick_label(
            "anchor_preservation",
            semantic_labels,
            fallback=_anchor_label(expected_write=expected_write, actual_write=actual_write, anchor_after=anchor_after),
        ),
    }
    dimension_scores = {key: LABEL_TO_SCORE[label] for key, label in dimension_labels.items()}
    raw_score = sum(WEIGHTS[key] * dimension_scores[key] for key in WEIGHTS)
    capped_label = _label_for_score(raw_score)
    hard_cap = None
    if expected_write and dimension_labels["should_write"] == "bad":
        capped_label = "bad"
        hard_cap = "missed_write"
    elif not expected_write and dimension_labels["should_not_write"] == "bad":
        capped_label = "bad"
        hard_cap = "unexpected_write"

    reasons: list[str] = []
    if expected_write and dimension_labels["should_write"] == "bad":
        reasons.append("missed_write")
    if not expected_write and dimension_labels["should_not_write"] == "bad":
        reasons.append("unexpected_write")
    if dimension_labels["type_correctness"] == "bad":
        reasons.append("wrong_type")
    if dimension_labels["scope_correctness"] == "bad":
        reasons.append("wrong_scope")
    if dimension_labels["anchor_preservation"] == "bad":
        reasons.append("missing_anchor")

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
            "persist_summary": persist_summary,
        },
    }


def _should_write_label(*, expected_write: bool, actual_write: bool) -> str:
    if not expected_write:
        return "weak"
    return "good" if actual_write else "bad"


def _should_not_write_label(*, expected_write: bool, actual_write: bool) -> str:
    if expected_write:
        return "weak"
    return "good" if not actual_write else "bad"


def _type_label(*, expected_type: Any, actual_type: str, actual_write: bool) -> str:
    if expected_type is None and not actual_write:
        return "weak"
    if expected_type is None:
        return "bad"
    return "good" if actual_type == str(expected_type) else "bad"


def _scope_label(*, expected_scope: Any, actual_scope: str, actual_write: bool) -> str:
    if expected_scope is None and not actual_write:
        return "weak"
    if expected_scope is None:
        return "bad"
    return "good" if actual_scope == str(expected_scope) else "bad"


def _anchor_label(*, expected_write: bool, actual_write: bool, anchor_after: Any) -> str:
    if not expected_write:
        return "weak"
    if not actual_write:
        return "bad"
    return "good" if isinstance(anchor_after, str) and anchor_after.strip() else "bad"


def _pick_label(name: str, labels: dict[str, str], *, fallback: str) -> str:
    label = labels.get(name, fallback)
    if label not in ALLOWED_LABELS:
        raise ValueError(f"Unsupported long-term memory label for {name}: {label}")
    return label


def _label_for_score(score: float) -> str:
    if score >= 0.80:
        return "good"
    if score >= 0.45:
        return "weak"
    return "bad"
