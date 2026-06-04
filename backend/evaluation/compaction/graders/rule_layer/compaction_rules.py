from __future__ import annotations

from typing import Any


LABEL_TO_SCORE = {"good": 1.0, "weak": 0.5, "bad": 0.0}
WEIGHTS = {
    "key_info_preserved": 0.35,
    "anchor_recoverability": 0.25,
    "post_compaction_sufficiency": 0.25,
    "pre_compaction_extraction_coverage": 0.15,
}
ALLOWED_LABELS = set(LABEL_TO_SCORE)


def grade_compaction_case(
    case: dict[str, Any],
    *,
    semantic_labels: dict[str, str] | None = None,
) -> dict[str, Any]:
    semantic_labels = semantic_labels or {}
    pre_summary = dict(case.get("pre_compaction_summary") or {})
    post_summary = dict(case.get("post_compaction_summary") or {})
    extraction_summary = dict(case.get("pre_compaction_extraction_summary") or {})

    dimension_labels = {
        "key_info_preserved": _pick_label(
            "key_info_preserved",
            semantic_labels,
            fallback=_bool_label(post_summary.get("key_info_preserved")),
        ),
        "anchor_recoverability": _pick_label(
            "anchor_recoverability",
            semantic_labels,
            fallback=_anchor_label(case, post_summary),
        ),
        "post_compaction_sufficiency": _pick_label(
            "post_compaction_sufficiency",
            semantic_labels,
            fallback=_bool_label(post_summary.get("sufficient_for_judgement")),
        ),
        "pre_compaction_extraction_coverage": _pick_label(
            "pre_compaction_extraction_coverage",
            semantic_labels,
            fallback=_extraction_label(extraction_summary),
        ),
    }
    dimension_scores = {key: LABEL_TO_SCORE[label] for key, label in dimension_labels.items()}
    raw_score = sum(WEIGHTS[key] * dimension_scores[key] for key in WEIGHTS)
    capped_label = _label_for_score(raw_score)
    hard_cap = None
    if dimension_labels["key_info_preserved"] == "bad":
        capped_label = "bad"
        hard_cap = "lost_key_info"

    reasons: list[str] = []
    if dimension_labels["key_info_preserved"] == "bad":
        reasons.append("lost_key_info")
    if dimension_labels["anchor_recoverability"] == "bad":
        reasons.append("lost_anchor")
    if dimension_labels["post_compaction_sufficiency"] == "bad":
        reasons.append("insufficient_post_context")
    if dimension_labels["pre_compaction_extraction_coverage"] == "bad":
        reasons.append("extraction_missed")

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
            "pre_summary": pre_summary,
            "post_summary": post_summary,
            "extraction_summary": extraction_summary,
        },
    }


def _bool_label(value: Any) -> str:
    if value is True:
        return "good"
    if value is False:
        return "bad"
    return "weak"


def _anchor_label(case: dict[str, Any], post_summary: dict[str, Any]) -> str:
    if not case.get("expected_anchor_required"):
        return "weak"
    return "good" if bool(post_summary.get("anchor_recoverable")) else "bad"


def _extraction_label(extraction_summary: dict[str, Any]) -> str:
    status = str(extraction_summary.get("coverage_status") or "").strip().lower()
    if status in ALLOWED_LABELS:
        return status
    if extraction_summary.get("coverage_complete") is True:
        return "good"
    if extraction_summary.get("coverage_complete") is False:
        return "bad"
    return "weak"


def _pick_label(name: str, labels: dict[str, str], *, fallback: str) -> str:
    label = labels.get(name, fallback)
    if label not in ALLOWED_LABELS:
        raise ValueError(f"Unsupported compaction label for {name}: {label}")
    return label


def _label_for_score(score: float) -> str:
    if score >= 0.80:
        return "good"
    if score >= 0.45:
        return "weak"
    return "bad"
