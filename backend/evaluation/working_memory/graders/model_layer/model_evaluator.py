from __future__ import annotations

from typing import Any

from evaluation.core.types import EvalCase, ModelEvalResult
from evaluation.working_memory.graders.model_layer.llm_runtime import WorkingMemoryLLMRuntime


class WorkingMemoryModelEvaluator:
    def __init__(
        self,
        *,
        use_llm: bool = False,
        label_overrides: dict[str, dict[str, str]] | None = None,
        llm_metadata_overrides: dict[str, dict[str, Any]] | None = None,
    ) -> None:
        self._runtime = WorkingMemoryLLMRuntime() if use_llm else None
        self._label_overrides = label_overrides or {}
        self._llm_metadata_overrides = llm_metadata_overrides or {}

    def evaluate(self, case: EvalCase) -> ModelEvalResult:
        case_id = str(case.get("case_id") or "")
        if self._runtime is None:
            return {
                "labels": self._label_overrides.get(case_id),
                "metadata": self._llm_metadata_overrides.get(case_id, {}),
            }
        try:
            runtime_result = self._runtime.grade_case(dict(case))
        except Exception as exc:
            runtime_result = {"labels": {}, "responses": {}, "error": str(exc)}
        return {
            "labels": self._label_overrides.get(case_id) or runtime_result.get("labels"),
            "metadata": self._llm_metadata_overrides.get(case_id) or runtime_result,
        }
