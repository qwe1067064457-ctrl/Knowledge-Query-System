from __future__ import annotations

from evaluation.core.types import EvalCase, RuleEvalResult
from evaluation.working_memory.graders.rule_layer.working_memory_rules import grade_working_memory_case


class WorkingMemoryRuleEvaluator:
    def evaluate(self, case: EvalCase) -> RuleEvalResult:
        return grade_working_memory_case(dict(case))
