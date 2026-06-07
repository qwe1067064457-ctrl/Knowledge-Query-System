from __future__ import annotations

from workflow.orchestrated.execution_layer.workers.base import BaseWorker


class ReviewSummaryWorker(BaseWorker):
    name = "review_summary"
    description = "Summarize review findings for local unit consumption."

    def run(self, evaluation):
        if hasattr(evaluation, "review_findings"):
            return {
                "status": getattr(evaluation, "status", "unknown"),
                "review_findings": [dict(item) for item in getattr(evaluation, "review_findings", ())],
            }
        data = dict(evaluation or {})
        return {
            "status": str(data.get("status", "unknown")),
            "review_findings": [dict(item) for item in data.get("review_findings", ()) or ()],
        }

