from __future__ import annotations

from typing import Any


def route_human_review(*, case: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    reasons: list[str] = []
    if result["label"] == "bad":
        reasons.append("compaction_bad_case")
    if case.get("user_feedback") == "dislike" and result["label"] == "good":
        reasons.append("dislike_high_score")
    metadata = result.get("grader_metadata", {}).get("model_result_meta", {})
    responses = metadata.get("responses")
    if isinstance(responses, dict):
        confidences = [
            float(payload.get("confidence"))
            for payload in responses.values()
            if isinstance(payload, dict) and "confidence" in payload
        ]
        if confidences and min(confidences) < 0.35:
            reasons.append("llm_low_confidence")
    return {
        "needs_human_review": bool(reasons),
        "reasons": reasons,
        "priority": "high" if reasons else "normal",
    }
