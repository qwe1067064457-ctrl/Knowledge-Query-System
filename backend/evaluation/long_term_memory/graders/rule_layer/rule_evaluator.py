from __future__ import annotations

from evaluation.core.types import EvalCase, RuleEvalResult
from evaluation.long_term_memory.graders.rule_layer.memory_rules import grade_long_term_memory_case


class LongTermMemoryRuleEvaluator:
    def evaluate(self, case: EvalCase) -> RuleEvalResult:
        return grade_long_term_memory_case(dict(case))
