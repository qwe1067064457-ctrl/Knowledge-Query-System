from __future__ import annotations

from workflow.orchestrated.execution_layer.workers.review.answer_constraint_worker import AnswerConstraintWorker
from workflow.orchestrated.execution_layer.workers.review.challenge_support_query_worker import ChallengeSupportQueryWorker
from workflow.orchestrated.execution_layer.workers.review.challenge_target_selection_worker import ChallengeTargetSelectionWorker
from workflow.orchestrated.execution_layer.workers.review.followup_retrieval_planner_worker import FollowupRetrievalPlannerWorker
from workflow.orchestrated.execution_layer.workers.review.review_re_evaluate_worker import ChallengeReEvaluateWorker
from workflow.orchestrated.execution_layer.workers.review.review_summary_worker import ReviewSummaryWorker
from workflow.orchestrated.execution_layer.workers.review.target_evidence_check_worker import TargetEvidenceCheckWorker
from workflow.orchestrated.execution_layer.workers.synthesis.caution_assembly_worker import CautionAssemblyWorker
from workflow.orchestrated.execution_layer.workers.synthesis.evidence_anchor_worker import EvidenceAnchorWorker
from workflow.orchestrated.execution_layer.workers.synthesis.finding_projection_worker import FindingProjectionWorker


def build_review_workers(*, review_worker):
    return (
        ChallengeTargetSelectionWorker(),
        ChallengeSupportQueryWorker(),
        TargetEvidenceCheckWorker(review_worker),
        ChallengeReEvaluateWorker(review_worker),
        FollowupRetrievalPlannerWorker(),
        ReviewSummaryWorker(),
        AnswerConstraintWorker(),
        FindingProjectionWorker(),
        EvidenceAnchorWorker(),
        CautionAssemblyWorker(),
    )
