from __future__ import annotations

from typing import Protocol

from .types import EvalCase, ModelEvalResult


class ModelEvaluator(Protocol):
    def evaluate(self, case: EvalCase) -> ModelEvalResult | None: ...
