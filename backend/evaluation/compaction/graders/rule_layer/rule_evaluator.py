from __future__ import annotations

from evaluation.compaction.graders.rule_layer.compaction_rules import grade_compaction_case
from evaluation.core.types import EvalCase, RuleEvalResult


class CompactionRuleEvaluator:
    def evaluate(self, case: EvalCase) -> RuleEvalResult:
        return grade_compaction_case(dict(case))
