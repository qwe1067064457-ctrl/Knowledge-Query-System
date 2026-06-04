from __future__ import annotations

from typing import Any

from evaluation.long_term_memory.graders.rule_layer.memory_rules import grade_long_term_memory_case


def merge_dimension_labels(
    *,
    rule_labels: dict[str, str],
    model_labels: dict[str, str] | None,
) -> tuple[dict[str, str], dict[str, dict[str, Any]]]:
    final_labels: dict[str, str] = {}
    provenance: dict[str, dict[str, Any]] = {}
    model_labels = model_labels or {}
    for dimension, rule_label in rule_labels.items():
        model_label = model_labels.get(dimension)
        if model_label is None:
            final_labels[dimension] = rule_label
            provenance[dimension] = {
                "source": "rule_fallback",
                "rule_label": rule_label,
                "llm_label": None,
                "fallback_applied": True,
            }
        else:
            final_labels[dimension] = model_label
            provenance[dimension] = {
                "source": "model",
                "rule_label": rule_label,
                "llm_label": model_label,
                "fallback_applied": False,
            }
    return final_labels, provenance


def finalize_case_result(
    *,
    case: dict[str, Any],
    rule_result: dict[str, Any],
    model_labels: dict[str, str] | None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    final_labels, provenance = merge_dimension_labels(
        rule_labels=rule_result["dimension_labels"],
        model_labels=model_labels,
    )
    final_result = grade_long_term_memory_case(case, semantic_labels=final_labels)
    return final_result, {
        "dimensions": provenance,
        "hard_cap": final_result["metadata"].get("hard_cap"),
        "fallback_applied": any(item["fallback_applied"] for item in provenance.values()),
        "score_owner": "finalize_layer",
    }
