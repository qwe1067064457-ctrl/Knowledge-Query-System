from __future__ import annotations

from typing import Any


def route_human_review(*, case: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    reasons: list[str] = []
    retrieval = result["retrieval"]
    answer = result["answer"]
    feedback = case.get("user_feedback")
    grader_metadata = result.get("grader_metadata", {})
    model_result_meta = grader_metadata.get("model_result_meta", {})

    retrieval_conf = _lowest_confidence(model_result_meta.get("retrieval", {}))
    answer_conf = _lowest_confidence(model_result_meta.get("answer", {}))
    if retrieval_conf is not None and retrieval_conf < 0.35:
        reasons.append("retrieval_llm_low_confidence")
    if answer_conf is not None and answer_conf < 0.35:
        reasons.append("answer_llm_low_confidence")

    if feedback == "dislike" and answer["label"] == "good":
        reasons.append("dislike_high_score")
    if feedback == "like" and answer["label"] == "bad":
        reasons.append("like_low_score")
    if retrieval["label"] == "bad":
        reasons.append("retrieval_bad_case")
    if answer["label"] == "bad":
        reasons.append("answer_bad_case")

    priority = "normal"
    if {"answer_bad_case", "dislike_high_score"} & set(reasons):
        priority = "high"
    return {
        "needs_human_review": bool(reasons),
        "reasons": reasons,
        "priority": priority,
    }


def _lowest_confidence(metadata: dict[str, Any]) -> float | None:
    responses = metadata.get("responses")
    if not isinstance(responses, dict) or not responses:
        return None
    values: list[float] = []
    for payload in responses.values():
        if isinstance(payload, dict) and "confidence" in payload:
            values.append(float(payload["confidence"]))
    if not values:
        return None
    return min(values)
