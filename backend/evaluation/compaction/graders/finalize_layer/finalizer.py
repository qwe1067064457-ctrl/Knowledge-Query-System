from __future__ import annotations

from evaluation.compaction.graders.finalize_layer.adjudication_router import route_human_review
from evaluation.compaction.graders.finalize_layer.aggregation import finalize_case_result
from evaluation.core.types import EvalCase, FinalEvalResult, ModelEvalResult, RuleEvalResult


class CompactionFinalizer:
    def finalize(
        self,
        case: EvalCase,
        *,
        rule_result: RuleEvalResult,
        model_result: ModelEvalResult | None,
    ) -> FinalEvalResult:
        raw_case = dict(case)
        model_result = model_result or {}
        final_result, finalize_meta = finalize_case_result(
            case=raw_case,
            rule_result=rule_result,
            model_labels=model_result.get("labels"),
        )
        result: FinalEvalResult = {
            "case_id": str(raw_case["case_id"]),
            "trace_id": str(raw_case["trace_id"]),
            "source": str(raw_case["source"]),
            "topic": str(raw_case.get("topic") or "compaction"),
            "dimension_labels": final_result["dimension_labels"],
            "dimension_scores": final_result["dimension_scores"],
            "score": final_result["score"],
            "label": final_result["label"],
            "reasons": final_result["reasons"],
            "user_feedback": raw_case.get("user_feedback"),
            "grader_metadata": {
                "rule_result_meta": rule_result["metadata"],
                "model_result_meta": model_result.get("metadata", {}),
                "finalize_meta": {
                    **finalize_meta,
                    "policy": {
                        "mode": "parallel_merge",
                        "llm_failure_fallback": "rule_labels",
                    },
                    "final_result_meta": final_result["metadata"],
                },
            },
        }
        adjudication = route_human_review(case=raw_case, result=result)
        result["needs_human_review"] = adjudication["needs_human_review"]
        result["human_review_reasons"] = adjudication["reasons"]
        result["review_priority"] = adjudication["priority"]
        return result
