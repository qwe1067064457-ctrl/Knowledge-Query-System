from __future__ import annotations

from intent.classifier import classify_intent
from intent.control_signal import build_control_signal
from intent.model_adapter import INTENT_MODEL_EVIDENCE_ENV, IntentModelAdapter, is_model_evidence_enabled, merge_model_evidence
from intent.rule_confidence import calculate_rule_confidence
from intent.resolver import resolve_intent
from intent.task_compat import ResolvedTaskCompatibility, build_task_compat, infer_topology_from_legacy_task
from intent.types import (
    CandidateIntent,
    ContextState,
    ControlSignal,
    DecisionTrace,
    IntentAnalysis,
    IntentEvidence,
    IntentInput,
    IntentModifiers,
    MainIntent,
    ModelContext,
    ModelResult,
    RuleConfidence,
    ResolvedIntent,
    ResolvedTask,
    RuleMatch,
    SignalBuckets,
    SignalConfidence,
    TaskCandidate,
    TaskTopology,
)

__all__ = [
    "CandidateIntent",
    "ContextState",
    "ControlSignal",
    "DecisionTrace",
    "IntentAnalysis",
    "IntentModelAdapter",
    "IntentEvidence",
    "IntentInput",
    "IntentModifiers",
    "MainIntent",
    "ModelContext",
    "ModelResult",
    "RuleConfidence",
    "ResolvedIntent",
    "ResolvedTaskCompatibility",
    "ResolvedTask",
    "RuleMatch",
    "SignalBuckets",
    "SignalConfidence",
    "TaskCandidate",
    "TaskTopology",
    "INTENT_MODEL_EVIDENCE_ENV",
    "build_control_signal",
    "build_task_compat",
    "calculate_rule_confidence",
    "classify_intent",
    "infer_topology_from_legacy_task",
    "is_model_evidence_enabled",
    "merge_model_evidence",
    "resolve_intent",
]
