from __future__ import annotations

from typing import Any

from evaluation.core.types import EvalCase, ModelEvalResult

from evaluation.workflow_answer.model_layer.llm_runtime import WorkflowAnswerLLMRuntime


class WorkflowAnswerModelEvaluator:
    def __init__(
        self,
        *,
        use_llm: bool = False,
        retrieval_label_overrides: dict[str, dict[str, str]] | None = None,
        answer_label_overrides: dict[str, dict[str, str]] | None = None,
        retrieval_llm_metadata: dict[str, dict[str, Any]] | None = None,
        answer_llm_metadata: dict[str, dict[str, Any]] | None = None,
    ) -> None:
        self._runtime = WorkflowAnswerLLMRuntime() if use_llm else None
        self._retrieval_label_overrides = retrieval_label_overrides or {}
        self._answer_label_overrides = answer_label_overrides or {}
        self._retrieval_llm_metadata = retrieval_llm_metadata or {}
        self._answer_llm_metadata = answer_llm_metadata or {}

    def evaluate(self, case: EvalCase) -> ModelEvalResult:
        case_id = str(case.get("case_id") or "")
        if self._runtime is None:
            return {
                "retrieval_labels": self._retrieval_label_overrides.get(case_id),
                "answer_labels": self._answer_label_overrides.get(case_id),
                "retrieval_meta": self._retrieval_llm_metadata.get(case_id, {}),
                "answer_meta": self._answer_llm_metadata.get(case_id, {}),
            }

        try:
            runtime_labels = self._runtime.grade_case(dict(case))
        except Exception as exc:
            runtime_labels = {
                "retrieval": {"labels": {}, "responses": {}, "error": str(exc)},
                "answer": {"labels": {}, "responses": {}, "error": str(exc)},
            }

        return {
            "retrieval_labels": self._retrieval_label_overrides.get(case_id)
            or runtime_labels.get("retrieval", {}).get("labels"),
            "answer_labels": self._answer_label_overrides.get(case_id)
            or runtime_labels.get("answer", {}).get("labels"),
            "retrieval_meta": self._retrieval_llm_metadata.get(case_id)
            or runtime_labels.get("retrieval", {}),
            "answer_meta": self._answer_llm_metadata.get(case_id)
            or runtime_labels.get("answer", {}),
        }
