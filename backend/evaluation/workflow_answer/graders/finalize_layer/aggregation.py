from __future__ import annotations

from typing import Any

from evaluation.workflow_answer.graders.rule_layer.answer_rules import grade_answer_case
from evaluation.workflow_answer.graders.rule_layer.retrieval_rules import grade_retrieval_case


def merge_dimension_labels(
    *,
    rule_labels: dict[str, str],
    llm_labels: dict[str, str] | None,
) -> tuple[dict[str, str], dict[str, dict[str, Any]]]:
    final_labels: dict[str, str] = {}
    provenance: dict[str, dict[str, Any]] = {}
    llm_labels = llm_labels or {}

    for dimension, rule_label in rule_labels.items():
        llm_label = llm_labels.get(dimension)
        if llm_label is None:
            final_labels[dimension] = rule_label
            provenance[dimension] = {
                "source": "rule_fallback",
                "rule_label": rule_label,
                "llm_label": None,
                "fallback_applied": True,
            }
            continue

        final_labels[dimension] = llm_label
        provenance[dimension] = {
            "source": "model",
            "rule_label": rule_label,
            "llm_label": llm_label,
            "fallback_applied": False,
        }
    return final_labels, provenance


def finalize_case_result(
    *,
    case: dict[str, Any],
    retrieval_rule: dict[str, Any],
    answer_rule: dict[str, Any],
    retrieval_model_labels: dict[str, str] | None,
    answer_model_labels: dict[str, str] | None,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    retrieval_labels, retrieval_provenance = merge_dimension_labels(
        rule_labels=retrieval_rule["dimension_labels"],
        llm_labels=retrieval_model_labels,
    )
    answer_labels, answer_provenance = merge_dimension_labels(
        rule_labels=answer_rule["dimension_labels"],
        llm_labels=answer_model_labels,
    )

    retrieval_final = grade_retrieval_case(case, semantic_labels=retrieval_labels)
    answer_final = grade_answer_case(case, semantic_labels=answer_labels)
    finalize_meta = {
        "retrieval_dimensions": retrieval_provenance,
        "answer_dimensions": answer_provenance,
        "retrieval_hard_cap": retrieval_final["metadata"].get("hard_cap"),
        "answer_hard_cap": answer_final["metadata"].get("hard_cap"),
        "fallback_applied": any(
            detail["fallback_applied"]
            for detail in list(retrieval_provenance.values()) + list(answer_provenance.values())
        ),
        "score_owner": "finalize_layer",
    }
    return retrieval_final, answer_final, finalize_meta
