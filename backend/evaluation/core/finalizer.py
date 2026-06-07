from __future__ import annotations

from typing import Protocol

from .types import EvalCase, FinalEvalResult, ModelEvalResult, RuleEvalResult


class Finalizer(Protocol):
    def finalize(
        self,
        case: EvalCase,
        *,
        rule_result: RuleEvalResult,
        model_result: ModelEvalResult | None,
    ) -> FinalEvalResult: ...
