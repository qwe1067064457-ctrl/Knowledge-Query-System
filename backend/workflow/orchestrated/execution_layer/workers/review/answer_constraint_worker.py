from __future__ import annotations

from workflow.orchestrated.execution_layer.workers.base import BaseWorker


class AnswerConstraintWorker(BaseWorker):
    name = "answer_constraint"
    description = "Extract answer constraints from a review evaluation."

    def run(self, evaluation):
        if hasattr(evaluation, "answer_constraints"):
            return dict(getattr(evaluation, "answer_constraints", {}) or {})
        return dict((evaluation or {}).get("answer_constraints", {}))

