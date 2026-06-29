from __future__ import annotations

from intent.pipeline.classifier import classify_intent
from intent.pipeline.control_signal import build_control_signal
from intent.pipeline.evidence_quality_gate import evaluate_evidence_quality
from intent.pipeline.model_adapter import (
    INTENT_MODEL_EVIDENCE_ENV,
    IntentModelAdapter,
    is_model_evidence_enabled,
    merge_model_evidence,
)
from intent.pipeline.resolver import resolve_intent
from intent.pipeline.adjudication import IntentAdjudicator
from intent.schema.evidence_types import AdjudicationResult, CaseLevelOutcome, EvidenceQualityReport, TypedEvidence
from intent.pipeline.rule_confidence import calculate_rule_confidence
from intent.pipeline.task_compat import ResolvedTaskCompatibility, build_task_compat, infer_topology_from_legacy_task
from intent.schema.intent_types import (
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
    "AdjudicationResult",
    "CaseLevelOutcome",
    "ContextState",
    "ControlSignal",
    "DecisionTrace",
    "IntentAnalysis",
    "IntentAdjudicator",
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
    "EvidenceQualityReport",
    "TypedEvidence",
    "INTENT_MODEL_EVIDENCE_ENV",
    "build_control_signal",
    "build_task_compat",
    "calculate_rule_confidence",
    "classify_intent",
    "evaluate_evidence_quality",
    "infer_topology_from_legacy_task",
    "is_model_evidence_enabled",
    "merge_model_evidence",
    "resolve_intent",
]
