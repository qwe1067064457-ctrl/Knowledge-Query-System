from __future__ import annotations

from typing import Protocol

from .types import EvalCase, RuleEvalResult


class RuleEvaluator(Protocol):
    def evaluate(self, case: EvalCase) -> RuleEvalResult: ...
