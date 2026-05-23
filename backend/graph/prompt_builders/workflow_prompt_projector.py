"""
Project workflow payloads into prompt-facing behavior and result instructions.
"""
from __future__ import annotations

from workflow import WorkflowPlan


def build_answer_behavior_rules_from_workflow(plan: WorkflowPlan) -> list[str]:
    instructions: list[str] = []

    if plan.should_ask_clarification_first:
        instructions.append(
            "The current request is not ready for full execution yet. Ask a concise clarification question first and do not continue into a substantive answer."
        )
        if plan.trace.missing_context_types:
            missing = ", ".join(plan.trace.missing_context_types)
            instructions.append(f"Focus the clarification on these missing context types: {missing}.")

    if plan.handling_mode == "challenge":
        instructions.append(
            "Treat this as a challenge/correction turn. Re-evaluate the disputed point carefully, explain the basis, and avoid defending the previous answer blindly."
        )
    elif plan.handling_mode == "scope_info":
        instructions.append(
            "Treat this as a scope/capability question. Answer about what the system can or cannot do instead of executing the underlying task."
        )
    elif plan.handling_mode == "unsupported":
        instructions.append(
            "Treat this as an unsupported request. Refuse the operation briefly and, when possible, suggest a safer alternative."
        )

    if plan.route == "orchestrated":
        instructions.append(
            "This request requires explicit execution organization. Make the stages or subtask order visible before giving the final answer."
        )
    elif plan.route == "qa":
        instructions.append(
            "This request should stay within a single-turn answer flow. Keep the execution lightweight and avoid unnecessary planning narration."
        )
    elif plan.route == "chat":
        instructions.append(
            "This is a chat turn. Respond naturally and do not over-structure the answer."
        )

    if plan.use_planner:
        instructions.append("Use an internal lightweight plan before answering so the reasoning order is stable.")
    if plan.decompose_query:
        instructions.append("Cover each sub-question or subtask explicitly so no requested branch is skipped.")
    if plan.cite_sources:
        instructions.append("Provide supporting basis or citations when available, and make the grounding visible instead of answering from bare assertion.")
    if plan.use_context:
        instructions.append("Use the current conversation context and do not treat this as a standalone fresh request.")
    return instructions


def build_answer_result_projection_rules_from_workflow(payload) -> list[str]:
    instructions: list[str] = []
    context_summary = payload.context_summary_view()
    plan_summary = payload.plan_summary_view()
    review_summary = payload.review_summary_view()
    evidence_summary = payload.evidence_summary_view()

    if context_summary.binding_summary != "not_applicable":
        instructions.append(
            f"Current binding summary: {context_summary.binding_summary}. Keep the answer anchored to the resolved target context."
        )
    if plan_summary.planning_mode != "not_applicable":
        instructions.append(
            f"Current planning summary: mode={plan_summary.planning_mode}, steps={plan_summary.step_count}, checkpoints={plan_summary.checkpoint_count}. Preserve this execution organization in the answer."
        )
        if plan_summary.fallback_used:
            instructions.append(
                "Planning fell back to a conservative structure. Keep the answer compact and avoid over-claiming hidden execution detail."
            )
    if review_summary.review_mode != "not_applicable":
        instructions.append(
            f"Current review summary: mode={review_summary.review_mode}, scope={review_summary.review_scope}, confidence={review_summary.review_confidence}, status={review_summary.status_summary}."
        )
        if review_summary.needs_more_evidence_target_count:
            instructions.append(
                f"There are still {review_summary.needs_more_evidence_target_count} target(s) needing more evidence. Acknowledge uncertainty explicitly."
            )
        if review_summary.follow_up_retrieval_attempted:
            instructions.append(
                "A follow-up retrieval was attempted during review. Reflect any remaining uncertainty rather than implying the review was fully definitive."
            )
    if evidence_summary.retrieval_quality_status != "not_applicable":
        instructions.append(
            f"Current evidence summary: quality={evidence_summary.retrieval_quality_status}, evidences={evidence_summary.merged_evidence_count}, sources={evidence_summary.source_ref_count}."
        )
        if evidence_summary.missing_evidence:
            instructions.append(
                "The evidence bundle is still incomplete. Do not overstate certainty and call out missing support when needed."
            )
    return instructions
