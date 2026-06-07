from __future__ import annotations

from typing import Any


LABEL_TO_SCORE = {"good": 1.0, "weak": 0.5, "bad": 0.0}
WEIGHTS = {
    "answered": 0.25,
    "grounded": 0.30,
    "consistency_with_evidence": 0.20,
    "constraint_coverage": 0.15,
    "no_hallucination": 0.10,
}
ALLOWED_LABELS = set(LABEL_TO_SCORE)


def grade_answer_case(
    case: dict[str, Any],
    *,
    semantic_labels: dict[str, str] | None = None,
) -> dict[str, Any]:
    semantic_labels = semantic_labels or {}
    evidence_summary = dict(case.get("knowledge_evidence_summary") or {})
    answer_text = str(case.get("answer_text") or "").strip()

    dimension_labels = {
        "answered": _pick_label("answered", semantic_labels, fallback=_heuristic_answered_label(answer_text)),
        "grounded": _pick_label("grounded", semantic_labels, fallback=_heuristic_grounded_label(case, evidence_summary)),
        "consistency_with_evidence": _pick_label(
            "consistency_with_evidence",
            semantic_labels,
            fallback=_heuristic_consistency_label(evidence_summary),
        ),
        "constraint_coverage": _pick_label(
            "constraint_coverage",
            semantic_labels,
            fallback=_heuristic_constraint_coverage_label(answer_text),
        ),
        "no_hallucination": _pick_label(
            "no_hallucination",
            semantic_labels,
            fallback=_heuristic_hallucination_label(answer_text, evidence_summary),
        ),
    }
    dimension_scores = {key: LABEL_TO_SCORE[label] for key, label in dimension_labels.items()}
    raw_score = sum(WEIGHTS[key] * dimension_scores[key] for key in WEIGHTS)
    capped_label = _label_for_score(raw_score)
    hard_cap = None
    if dimension_labels["answered"] == "bad":
        capped_label = "bad"
        hard_cap = "answered_bad"
    elif dimension_labels["consistency_with_evidence"] == "bad" and capped_label == "good":
        capped_label = "weak"
        hard_cap = "consistency_bad"
    elif dimension_labels["no_hallucination"] == "bad" and capped_label == "good":
        capped_label = "weak"
        hard_cap = "hallucination_bad"

    reasons: list[str] = []
    if dimension_labels["answered"] == "bad":
        reasons.append("missed_question")
    if dimension_labels["grounded"] == "bad":
        reasons.append("ungrounded")
    if dimension_labels["consistency_with_evidence"] == "bad":
        reasons.append("conflict_with_evidence")
    if dimension_labels["constraint_coverage"] == "bad":
        reasons.append("missed_constraint")
    if dimension_labels["no_hallucination"] == "bad":
        reasons.append("hallucination")

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
                name: name not in semantic_labels
                for name in (
                    "answered",
                    "grounded",
                    "consistency_with_evidence",
                    "constraint_coverage",
                    "no_hallucination",
                )
            },
            "core_summary_present": bool(case.get("core_summary_present")),
            "evidence_summary": evidence_summary,
        },
    }


def _pick_label(name: str, labels: dict[str, str], *, fallback: str) -> str:
    label = labels.get(name, fallback)
    if label not in ALLOWED_LABELS:
        raise ValueError(f"Unsupported answer label for {name}: {label}")
    return label


def _heuristic_answered_label(answer_text: str) -> str:
    if not answer_text:
        return "bad"
    return "weak"


def _heuristic_grounded_label(case: dict[str, Any], evidence_summary: dict[str, Any]) -> str:
    if not case.get("answer_text"):
        return "bad"
    if bool(case.get("core_summary_present")) and int(evidence_summary.get("merged_evidence_count", 0) or 0) > 0:
        return "good"
    status = str(evidence_summary.get("retrieval_quality_status") or "").strip().lower()
    if status == "bad":
        return "bad"
    return "weak"


def _heuristic_consistency_label(evidence_summary: dict[str, Any]) -> str:
    status = str(evidence_summary.get("retrieval_quality_status") or "").strip().lower()
    if status == "bad":
        return "weak"
    if status == "good":
        return "good"
    return "weak"


def _heuristic_constraint_coverage_label(answer_text: str) -> str:
    if not answer_text:
        return "bad"
    return "weak"


def _heuristic_hallucination_label(answer_text: str, evidence_summary: dict[str, Any]) -> str:
    if not answer_text:
        return "bad"
    if int(evidence_summary.get("merged_evidence_count", 0) or 0) <= 0:
        return "weak"
    return "good"


def _label_for_score(score: float) -> str:
    if score >= 0.80:
        return "good"
    if score >= 0.45:
        return "weak"
    return "bad"
