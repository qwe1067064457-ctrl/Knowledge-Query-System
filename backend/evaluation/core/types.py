from __future__ import annotations

from typing import Any, TypedDict


class EvalCase(TypedDict, total=False):
    case_id: str
    trace_id: str
    source: str
    topic: str
    payload: dict[str, Any]


class RuleEvalResult(TypedDict, total=False):
    labels: dict[str, Any]
    metadata: dict[str, Any]


class ModelEvalResult(TypedDict, total=False):
    labels: dict[str, Any]
    metadata: dict[str, Any]


class FinalEvalResult(TypedDict, total=False):
    case_id: str
    trace_id: str
    source: str
    topic: str
    dimension_labels: dict[str, Any]
    dimension_scores: dict[str, Any]
    score: float
    label: str
    reasons: list[str]
    grader_metadata: dict[str, Any]
    needs_human_review: bool
    human_review_reasons: list[str]
    review_priority: str
