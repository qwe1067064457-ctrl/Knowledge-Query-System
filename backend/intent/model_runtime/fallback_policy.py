from __future__ import annotations

import os

from intent.schema.intent_types import ControlSignal, IntentEvidence, ResolvedIntent


INTENT_LLM_FALLBACK_ENV = "INTENT_LLM_FALLBACK_ENABLED"


def is_llm_fallback_enabled() -> bool:
    value = os.getenv(INTENT_LLM_FALLBACK_ENV, "").strip().lower()
    return value in {"1", "true", "yes", "on"}


def should_trigger_llm_fallback(
    evidence: IntentEvidence,
    *,
    resolved: ResolvedIntent,
    control: ControlSignal,
) -> bool:
    model_result = evidence.model_result
    if model_result is None or not model_result.valid:
        return False
    if model_result.low_confidence:
        return True
    if _has_rule_model_conflict(evidence):
        return True
    if _hits_hard_residuals(model_result):
        return True
    if control.handling_mode in {"scope_info", "unsupported"} and model_result.confidence != "high":
        return True
    if resolved.task.topology == "staged" and model_result.confidence != "high":
        return True
    return False


def _has_rule_model_conflict(evidence: IntentEvidence) -> bool:
    model_result = evidence.model_result
    if model_result is None:
        return False
    intent_signals = set(evidence.signal_buckets.intent)
    if "ask_source" in intent_signals and float(model_result.modifier_scores.get("ask_source", 0.0)) < 0.15:
        return True
    if "challenge" in intent_signals and float(model_result.modifier_scores.get("challenge", 0.0)) < 0.15:
        return True
    if "out_of_scope" in evidence.signal_buckets.safety and float(model_result.safety_scores.get("out_of_scope", 0.0)) < 0.2:
        return True
    return False


def _hits_hard_residuals(model_result) -> bool:
    if float(model_result.modifier_scores.get("ask_source", 0.0)) >= 0.15:
        return True
    if float(model_result.task_shape_probs.get("compare", 0.0)) >= 0.2:
        return True
    if float(model_result.task_shape_probs.get("mixed", 0.0)) >= 0.2:
        return True
    if max(model_result.ambiguity_scores.values(), default=0.0) >= 0.2:
        return True
    return False
