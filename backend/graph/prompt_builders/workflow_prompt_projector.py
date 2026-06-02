"""
Project workflow payloads into answer signal filters and prompt-facing rules.
"""
from __future__ import annotations

from typing import Any

from workflow import WorkflowPlan
from workflow.orchestrated.answer_layer.projectors.answer_layer_projector import build_answer_assembly_package
from workflow.orchestrated.answer_layer.projectors.answer_prompt_block_builder import build_answer_prompt_blocks


def filter_answer_behavior_signals_from_workflow(plan: WorkflowPlan) -> dict[str, Any]:
    return {
        "ask_clarification_first": bool(plan.should_ask_clarification_first),
        "missing_context_types": tuple(plan.trace.missing_context_types),
        "handling_mode": plan.handling_mode,
        "route": plan.route,
        "use_planner": bool(plan.use_planner),
        "decompose_query": bool(plan.decompose_query),
        "cite_sources": bool(plan.cite_sources),
        "use_context": bool(plan.use_context),
    }


def render_behavior_rules_from_signals(signals: dict[str, Any]) -> list[str]:
    instructions: list[str] = []

    if signals.get("ask_clarification_first"):
        instructions.append(
            "The current request is not ready for full execution yet. Ask a concise clarification question first and do not continue into a substantive answer."
        )
        missing_context_types = tuple(signals.get("missing_context_types", ()) or ())
        if missing_context_types:
            missing = ", ".join(str(item) for item in missing_context_types)
            instructions.append(f"Focus the clarification on these missing context types: {missing}.")

    handling_mode = str(signals.get("handling_mode", "normal"))
    if handling_mode == "challenge":
        instructions.append(
            "Treat this as a challenge/correction turn. Re-evaluate the disputed point carefully, explain the basis, and avoid defending the previous answer blindly."
        )
    elif handling_mode == "scope_info":
        instructions.append(
            "Treat this as a scope/capability question. Answer about what the system can or cannot do instead of executing the underlying task."
        )
    elif handling_mode == "unsupported":
        instructions.append(
            "Treat this as an unsupported request. Refuse the operation briefly and, when possible, suggest a safer alternative."
        )

    route = str(signals.get("route", "qa"))
    if route == "orchestrated":
        instructions.append(
            "This request requires explicit execution organization. Make the stages or subtask order visible before giving the final answer."
        )
    elif route == "qa":
        instructions.append(
            "This request should stay within a single-turn answer flow. Keep the execution lightweight and avoid unnecessary planning narration."
        )
    elif route == "chat":
        instructions.append(
            "This is a chat turn. Respond naturally and do not over-structure the answer."
        )
    elif route == "reject":
        instructions.append(
            "This request should not enter the normal execution flow. Keep the response brief, explicit about the boundary, and do not continue into a substantive answer."
        )

    if signals.get("use_planner"):
        instructions.append("Use an internal lightweight plan before answering so the reasoning order is stable.")
    if signals.get("decompose_query"):
        instructions.append("Cover each sub-question or subtask explicitly so no requested branch is skipped.")
    if signals.get("cite_sources"):
        instructions.append("Provide supporting basis or citations when available, and make the grounding visible instead of answering from bare assertion.")
    if signals.get("use_context"):
        instructions.append("Use the current conversation context and do not treat this as a standalone fresh request.")
    return instructions


def build_answer_behavior_rules_from_workflow(plan: WorkflowPlan) -> list[str]:
    return render_behavior_rules_from_signals(filter_answer_behavior_signals_from_workflow(plan))


def filter_answer_result_signals_from_workflow(payload) -> dict[str, Any]:
    context_summary = payload.context_summary_view()
    plan_summary = payload.plan_summary_view()
    review_summary = payload.challenge_result_summary_view()
    evidence_summary = payload.evidence_summary_view()
    key_events = set(getattr(payload, "key_events", ()) or ())
    answer_constraints = dict(getattr(payload, "answer_constraints", {}) or {})
    route = str(getattr(payload, "route", "") or "")

    visible_key_events = tuple(
        event
        for event in (
            "clarification_required",
            "binding_ambiguous",
            "insufficient_evidence",
            "policy_reject",
            "capability_reject",
        )
        if event in key_events
    )
    return {
        "route": route,
        "status": str(getattr(payload, "status", "ready") or "ready"),
        "knowledge_scope_status": str(getattr(payload, "knowledge_scope_status", "resolved") or "resolved"),
        "binding_summary": context_summary.binding_summary,
        "planning_mode": plan_summary.planning_mode,
        "planning_step_count": plan_summary.step_count,
        "planning_checkpoint_count": plan_summary.checkpoint_count,
        "planning_fallback_used": bool(plan_summary.fallback_used),
        "review_mode": review_summary.review_mode,
        "review_scope": review_summary.review_scope,
        "review_confidence": review_summary.review_confidence,
        "review_status_summary": review_summary.status_summary,
        "review_needs_more_evidence_target_count": review_summary.needs_more_evidence_target_count,
        "review_follow_up_retrieval_attempted": bool(review_summary.follow_up_retrieval_attempted),
        "review_follow_up_retrieval_improved": bool(review_summary.follow_up_retrieval_improved),
        "evidence_quality_status": evidence_summary.retrieval_quality_status,
        "evidence_missing": bool(evidence_summary.missing_evidence),
        "visible_key_events": visible_key_events,
        "allow_substantive_answer": answer_constraints.get("allow_substantive_answer"),
        "must_ask_clarification_first": bool(answer_constraints.get("must_ask_clarification_first", False)),
        "must_explain_boundary": bool(answer_constraints.get("must_explain_boundary", False)),
        "must_offer_safe_alternative": bool(answer_constraints.get("must_offer_safe_alternative", False)),
        "reject_reason_code": context_summary.reject_reason_code,
        "reject_reason": context_summary.reject_reason,
        "orchestrated_prompt_blocks": _orchestrated_prompt_blocks(payload) if route == "orchestrated" else (),
    }


def _orchestrated_prompt_blocks(payload) -> tuple[str, ...]:
    package = build_answer_assembly_package(
        question=str(payload.plan_bundle_obj().goal or "") or "Current orchestrated request",
        payload=payload,
    )
    prompt_blocks = build_answer_prompt_blocks(package)
    return tuple(prompt_blocks.as_ordered_blocks())


def render_result_rules_from_signals(signals: dict[str, Any]) -> list[str]:
    instructions: list[str] = []

    if signals.get("knowledge_scope_status") == "needs_clarification":
        instructions.append(
            "Knowledge scope is still unresolved. Ask a concise clarification before giving any substantive answer."
        )
    if signals.get("must_ask_clarification_first") or "clarification_required" in signals.get("visible_key_events", ()):
        instructions.append(
            "The workflow requires clarification before proceeding. Ask the clarification directly and stop there."
        )

    binding_summary = str(signals.get("binding_summary", "not_applicable"))
    if binding_summary != "not_applicable":
        instructions.append(
            f"Current binding summary: {binding_summary}. Keep the answer anchored to the resolved target context."
        )
    if "binding_ambiguous" in signals.get("visible_key_events", ()) and "clarification_required" not in signals.get("visible_key_events", ()):
        instructions.append(
            "The current target alignment is still ambiguous. Avoid over-committing to a single historical target unless the answer makes the uncertainty explicit."
        )

    if str(signals.get("route", "")) == "orchestrated" and str(signals.get("planning_mode", "not_applicable")) != "not_applicable":
        instructions.append(
            f"Current planning summary: mode={signals['planning_mode']}, steps={signals['planning_step_count']}, checkpoints={signals['planning_checkpoint_count']}. Preserve this execution organization in the answer."
        )
        if signals.get("planning_fallback_used"):
            instructions.append(
                "Planning fell back to a conservative structure. Keep the answer compact and avoid over-claiming hidden execution detail."
            )

    if str(signals.get("review_mode", "not_applicable")) != "not_applicable":
        instructions.append(
            f"Current review summary: mode={signals['review_mode']}, scope={signals['review_scope']}, confidence={signals['review_confidence']}, status={signals['review_status_summary']}."
        )
        if int(signals.get("review_needs_more_evidence_target_count", 0) or 0):
            instructions.append(
                f"There are still {signals['review_needs_more_evidence_target_count']} target(s) needing more evidence. Acknowledge uncertainty explicitly."
            )
        if signals.get("review_follow_up_retrieval_attempted"):
            if signals.get("review_follow_up_retrieval_improved"):
                instructions.append(
                    "A follow-up retrieval improved coverage during review. Prefer the improved evidence set, but keep the final certainty aligned with the review confidence."
                )
            else:
                instructions.append(
                    "A follow-up retrieval was attempted during review but did not fully resolve the evidence gap. Reflect any remaining uncertainty rather than implying the review was fully definitive."
                )

    if "insufficient_evidence" in signals.get("visible_key_events", ()) or signals.get("review_status_summary") == "insufficient_evidence":
        instructions.append(
            "Evidence remains insufficient for a definitive answer. Be explicit about uncertainty and avoid over-claiming."
        )

    evidence_quality_status = str(signals.get("evidence_quality_status", "not_applicable"))
    if evidence_quality_status != "not_applicable":
        if evidence_quality_status in {"weak", "bad"}:
            instructions.append(
                f"Current evidence quality is {evidence_quality_status}. Prefer a conservative answer posture and avoid overstating unsupported details."
            )
        if signals.get("evidence_missing") or "insufficient_evidence" in signals.get("visible_key_events", ()):
            instructions.append(
                "The evidence bundle is still incomplete. Do not overstate certainty and call out missing support when needed."
            )

    if signals.get("reject_reason_code"):
        instructions.append(
            f"Current reject summary: code={signals['reject_reason_code']}, reason={signals['reject_reason'] or 'not_provided'}."
        )
        if signals.get("must_explain_boundary"):
            instructions.append(
                "Explain the boundary briefly and do not continue into a substantive answer."
            )
        if signals.get("must_offer_safe_alternative"):
            instructions.append(
                "When possible, offer a safer alternative instead of continuing the rejected operation."
            )
        if signals.get("allow_substantive_answer") is False:
            instructions.append(
                "Do not provide a substantive answer beyond the allowed boundary explanation."
            )

    instructions.extend(str(item) for item in signals.get("orchestrated_prompt_blocks", ()) or ())
    return instructions


def build_answer_result_projection_rules_from_workflow(payload) -> list[str]:
    return render_result_rules_from_signals(filter_answer_result_signals_from_workflow(payload))
