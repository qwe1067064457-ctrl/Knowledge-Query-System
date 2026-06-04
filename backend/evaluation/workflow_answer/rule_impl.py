from __future__ import annotations

from typing import Any

from evaluation.core.types import EvalCase, RuleEvalResult

from evaluation.workflow_answer.rule_layer.answer_rules import grade_answer_case
from evaluation.workflow_answer.rule_layer.retrieval_rules import grade_retrieval_case


class WorkflowAnswerRuleEvaluator:
    def evaluate(self, case: EvalCase) -> RuleEvalResult:
        raw_case = _as_case_dict(case)
        return {
            "retrieval": grade_retrieval_case(raw_case),
            "answer": grade_answer_case(raw_case),
        }


def _as_case_dict(case: EvalCase) -> dict[str, Any]:
    return dict(case)
