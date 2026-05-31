from __future__ import annotations

from workflow.orchestrated.execution_layer.workers.base import BaseWorker
from workflow.types import EvidenceAssessmentResult


class FollowupRetrievalPlannerWorker(BaseWorker):
    name = "followup_retrieval_planner"
    description = "Plan follow-up retrieval when current evidence is insufficient."

    def run(self, evidence_assessment: dict):
        assessment = EvidenceAssessmentResult.from_dict(evidence_assessment)
        return {
            "needed": assessment.needs_follow_up_retrieval(),
            "target_refs": list(assessment.retrieve_target_refs()),
            "reason": str(assessment.retrieve_if_needed.get("reason", "not_needed")),
        }

