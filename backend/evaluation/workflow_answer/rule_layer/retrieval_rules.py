from __future__ import annotations

from typing import Any


LABEL_TO_SCORE = {"good": 1.0, "weak": 0.5, "bad": 0.0}
WEIGHTS = {
    "presence": 0.20,
    "relevance": 0.35,
    "sufficiency": 0.25,
    "usability": 0.20,
}
ALLOWED_LABELS = set(LABEL_TO_SCORE)


def grade_retrieval_case(
    case: dict[str, Any],
    *,
    semantic_labels: dict[str, str] | None = None,
) -> dict[str, Any]:
    summary = _evidence_summary(case)
    semantic_labels = semantic_labels or {}

    dimension_labels = {
        "presence": _presence_label(summary),
        "relevance": _pick_label("relevance", semantic_labels, fallback=_quality_status_label(summary)),
        "sufficiency": _pick_label("sufficiency", semantic_labels, fallback=_heuristic_sufficiency_label(summary)),
        "usability": _pick_label("usability", semantic_labels, fallback=_heuristic_usability_label(case, summary)),
    }
    dimension_scores = {key: LABEL_TO_SCORE[label] for key, label in dimension_labels.items()}
    raw_score = sum(WEIGHTS[key] * dimension_scores[key] for key in WEIGHTS)
    capped_label = _label_for_score(raw_score)
    hard_cap = None
    if dimension_labels["presence"] == "bad":
        capped_label = "bad"
        hard_cap = "presence_bad"
    elif dimension_labels["relevance"] == "bad" and capped_label == "good":
        capped_label = "weak"
        hard_cap = "relevance_bad"

    reasons: list[str] = []
    if dimension_labels["presence"] == "bad":
        reasons.append("no_evidence")
    if dimension_labels["relevance"] == "bad":
        reasons.append("off_topic")
    if dimension_labels["sufficiency"] == "bad":
        reasons.append("insufficient_evidence")
    if dimension_labels["usability"] == "bad":
        reasons.append("evidence_unused")

    return {
        "dimension_labels": dimension_labels,
        "dimension_scores": dimension_scores,
        "weights": dict(WEIGHTS),
        "score": round(raw_score, 4),
        "label": capped_label,
        "reasons": reasons,
        "metadata": {
            "hard_cap": hard_cap,
            "heuristic_labels": {
                "relevance": "relevance" not in semantic_labels,
                "sufficiency": "sufficiency" not in semantic_labels,
                "usability": "usability" not in semantic_labels,
            },
            "evidence_summary": summary,
        },
    }


def _evidence_summary(case: dict[str, Any]) -> dict[str, Any]:
    return dict(case.get("knowledge_evidence_summary") or {})


def _presence_label(summary: dict[str, Any]) -> str:
    evidence_count = int(summary.get("merged_evidence_count", 0) or 0)
    if evidence_count <= 0 or bool(summary.get("missing_evidence")):
        return "bad"
    if evidence_count == 1:
        return "weak"
    return "good"


def _quality_status_label(summary: dict[str, Any]) -> str:
    status = str(summary.get("retrieval_quality_status") or "").strip().lower()
    if status in ALLOWED_LABELS:
        return status
    return "weak"


def _heuristic_sufficiency_label(summary: dict[str, Any]) -> str:
    evidence_count = int(summary.get("merged_evidence_count", 0) or 0)
    query_units = int(summary.get("query_unit_count", 0) or 0)
    if evidence_count <= 0:
        return "bad"
    if bool(summary.get("missing_evidence")):
        return "bad"
    if evidence_count >= max(2, query_units):
        return "good"
    return "weak"


def _heuristic_usability_label(case: dict[str, Any], summary: dict[str, Any]) -> str:
    answer_text = str(case.get("answer_text") or "").strip()
    evidence_count = int(summary.get("merged_evidence_count", 0) or 0)
    if evidence_count <= 0:
        return "bad"
    if not answer_text:
        return "bad"
    return "weak"


def _pick_label(name: str, labels: dict[str, str], *, fallback: str) -> str:
    label = labels.get(name, fallback)
    if label not in ALLOWED_LABELS:
        raise ValueError(f"Unsupported retrieval label for {name}: {label}")
    return label


def _label_for_score(score: float) -> str:
    if score >= 0.80:
        return "good"
    if score >= 0.45:
        return "weak"
    return "bad"
