from __future__ import annotations

from typing import Any

from evaluation.core.types import EvalCase, FinalEvalResult, ModelEvalResult, RuleEvalResult

from evaluation.workflow_answer.finalize_layer.adjudication_router import route_human_review
from evaluation.workflow_answer.finalize_layer.aggregation import finalize_case_result


class WorkflowAnswerFinalizer:
    def finalize(
        self,
        case: EvalCase,
        *,
        rule_result: RuleEvalResult,
        model_result: ModelEvalResult | None,
    ) -> FinalEvalResult:
        raw_case = dict(case)
        model_result = model_result or {}
        retrieval, answer, finalize_meta = finalize_case_result(
            case=raw_case,
            retrieval_rule=rule_result["retrieval"],
            answer_rule=rule_result["answer"],
            retrieval_model_labels=model_result.get("retrieval_labels"),
            answer_model_labels=model_result.get("answer_labels"),
        )

        grader_metadata = {
            "rule_result_meta": {
                "retrieval": rule_result["retrieval"]["metadata"],
                "answer": rule_result["answer"]["metadata"],
            },
            "model_result_meta": {
                "retrieval": model_result.get("retrieval_meta", {}),
                "answer": model_result.get("answer_meta", {}),
            },
            "finalize_meta": {
                **finalize_meta,
                "policy": {
                    "mode": "parallel_merge",
                    "llm_failure_fallback": "rule_labels",
                },
                "retrieval_final_meta": retrieval["metadata"],
                "answer_final_meta": answer["metadata"],
            },
        }

        retrieval_output = {key: value for key, value in retrieval.items() if key != "metadata"}
        answer_output = {key: value for key, value in answer.items() if key != "metadata"}
        overall_score = round((float(retrieval_output["score"]) + float(answer_output["score"])) / 2, 4)
        overall_label = _overall_label(retrieval_output["label"], answer_output["label"])
        reasons = list(dict.fromkeys([*retrieval_output.get("reasons", []), *answer_output.get("reasons", [])]))
        result: FinalEvalResult = {
            "case_id": str(raw_case["case_id"]),
            "trace_id": str(raw_case["trace_id"]),
            "source": str(raw_case["source"]),
            "topic": str(raw_case.get("topic") or "workflow_answer"),
            "dimension_labels": {
                "retrieval": retrieval_output["label"],
                "answer": answer_output["label"],
            },
            "dimension_scores": {
                "retrieval": retrieval_output["score"],
                "answer": answer_output["score"],
            },
            "score": overall_score,
            "label": overall_label,
            "reasons": reasons,
            "user_feedback": raw_case.get("user_feedback"),
            "retrieval": retrieval_output,
            "answer": answer_output,
            "grader_metadata": grader_metadata,
        }
        adjudication = route_human_review(case=raw_case, result=result)
        result["needs_human_review"] = adjudication["needs_human_review"]
        result["human_review_reasons"] = adjudication["reasons"]
        result["review_priority"] = adjudication["priority"]
        return result


def _overall_label(retrieval_label: str, answer_label: str) -> str:
    if "bad" in {retrieval_label, answer_label}:
        return "bad"
    if "weak" in {retrieval_label, answer_label}:
        return "weak"
    return "good"
