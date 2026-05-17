from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal


MainIntent = Literal["qa", "chat", "system", "unsupported"]
TaskComplexity = Literal["simple", "compound", "complex"]
TaskTopology = Literal["single", "parallel_queries", "parallel_subtasks", "staged"]
TaskShape = Literal[
    "single_question",
    "multi_question",
    "compare",
    "summarize",
    "extract",
    "verify",
    "mixed",
    "none",
]
ContextDependency = Literal[
    "none",
    "history_reference",
    "previous_answer",
    "previous_retrieval",
    "ambiguous",
]
Route = Literal["rag", "chat", "direct", "agent", "reject"]
Mode = Literal["normal", "challenge", "capability", "clarify"]
PlanningLevel = Literal["none", "light", "full"]
Strength = Literal["high", "medium", "low"]
DecisionSource = Literal["rule", "model", "hybrid", "fallback"]
ClassifierMode = Literal["rule_only", "rule_plus_model", "model_first_with_rule_guard"]


@dataclass(frozen=True)
class ContextState:
    has_history: bool = False
    has_previous_answer: bool = False
    last_main_intent: MainIntent | None = None
    last_route: Route | None = None
    last_mode: Mode | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ModelContext:
    last_user_query: str = ""
    last_user_goal: str = ""
    last_answer_summary: str = ""
    last_assistant_claim: str = ""
    last_retrieval_summary: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class IntentInput:
    user_query: str
    context_state: ContextState = field(default_factory=ContextState)
    model_context: ModelContext = field(default_factory=ModelContext)

    def to_dict(self) -> dict[str, Any]:
        return {
            "user_query": self.user_query,
            "context_state": self.context_state.to_dict(),
            "model_context": self.model_context.to_dict(),
        }


@dataclass(frozen=True)
class RuleMatch:
    rule_id: str
    signal: str
    strength: Strength
    score: float
    matched_text: str
    source: Literal["rule"] = "rule"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CandidateIntent:
    intent: MainIntent
    score: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class TaskCandidate:
    complexity: TaskComplexity
    shape: TaskShape
    score: float
    topology: TaskTopology = "single"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class IntentModifiers:
    follow_up: bool = False
    challenge: bool = False
    soft_doubt: bool = False
    ask_source: bool = False
    ask_capability: bool = False
    needs_clarification: bool = False
    out_of_scope: bool = False

    def to_dict(self) -> dict[str, bool]:
        return asdict(self)


@dataclass(frozen=True)
class ModelResult:
    valid: bool
    candidate_intents: tuple[CandidateIntent, ...] = ()
    modifiers: IntentModifiers = field(default_factory=IntentModifiers)
    task_candidates: tuple[TaskCandidate, ...] = ()
    context_dependency: ContextDependency = "none"
    confidence: Strength = "low"
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "candidate_intents": [item.to_dict() for item in self.candidate_intents],
            "modifiers": self.modifiers.to_dict(),
            "task_candidates": [item.to_dict() for item in self.task_candidates],
            "context_dependency": self.context_dependency,
            "confidence": self.confidence,
            "reason": self.reason,
        }


@dataclass(frozen=True)
class ContextSignals:
    has_reference: bool = False
    has_previous_intent: bool = False
    has_implicit_history: bool = False
    is_direct_followup: bool = False
    previous_answer: bool = False
    previous_retrieval: bool = False
    ambiguous: bool = False
    none: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "none": self.none,
            "history_reference": self.has_reference,
            "previous_answer": self.previous_answer,
            "previous_retrieval": self.previous_retrieval,
            "ambiguous": self.ambiguous,
            "has_reference": self.has_reference,
            "has_previous_intent": self.has_previous_intent,
            "has_implicit_history": self.has_implicit_history,
            "is_direct_followup": self.is_direct_followup,
        }


@dataclass(frozen=True)
class SignalConfidence:
    signal: str
    base_score: float
    support_bonus: float
    conflict_penalty: float
    context_adjustment: float
    final_score: float
    level: Strength
    supporting_rule_ids: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RuleConfidence:
    signal_confidences: tuple[SignalConfidence, ...] = ()
    final_signal: str = ""
    final_score: float = 0.0
    final_level: Strength = "low"
    explanation: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "signal_confidences": [item.to_dict() for item in self.signal_confidences],
            "final_signal": self.final_signal,
            "final_score": self.final_score,
            "final_level": self.final_level,
            "explanation": list(self.explanation),
        }


@dataclass(frozen=True)
class SignalBuckets:
    intent: tuple[str, ...] = ()
    task: tuple[str, ...] = ()
    context: tuple[str, ...] = ()
    safety: tuple[str, ...] = ()

    def all_signals(self) -> tuple[str, ...]:
        ordered = []
        for signal in (*self.intent, *self.task, *self.context, *self.safety):
            if signal not in ordered:
                ordered.append(signal)
        return tuple(ordered)

    def to_dict(self) -> dict[str, Any]:
        return {
            "intent": list(self.intent),
            "task": list(self.task),
            "context": list(self.context),
            "safety": list(self.safety),
        }


@dataclass(frozen=True)
class EvidenceMeta:
    classifier_mode: ClassifierMode
    matched_rules: tuple[RuleMatch, ...] = ()
    rule_confidence: RuleConfidence | None = None
    model_result: ModelResult | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "classifier_mode": self.classifier_mode,
            "matched_rules": [item.to_dict() for item in self.matched_rules],
            "rule_confidence": self.rule_confidence.to_dict() if self.rule_confidence else None,
            "model_result": self.model_result.to_dict() if self.model_result else None,
        }


@dataclass(frozen=True)
class IntentEvidenceView:
    raw_signals: tuple[str, ...] = ()
    candidate_intents: tuple[CandidateIntent, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "raw_signals": list(self.raw_signals),
            "candidate_intents": [item.to_dict() for item in self.candidate_intents],
        }


@dataclass(frozen=True)
class TaskEvidenceView:
    raw_signals: tuple[str, ...] = ()
    task_candidates: tuple[TaskCandidate, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "raw_signals": list(self.raw_signals),
            "task_candidates": [item.to_dict() for item in self.task_candidates],
        }


@dataclass(frozen=True)
class ContextEvidenceView:
    raw_signals: tuple[str, ...] = ()
    dependency_signals: dict[str, bool] = field(default_factory=dict)
    context_signals: ContextSignals = field(default_factory=ContextSignals)

    def to_dict(self) -> dict[str, Any]:
        return {
            "raw_signals": list(self.raw_signals),
            "dependency_signals": dict(self.dependency_signals),
            "context_signals": self.context_signals.to_dict(),
        }


@dataclass(frozen=True)
class SafetyEvidenceView:
    raw_signals: tuple[str, ...] = ()
    unsupported_signals: dict[str, bool] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "raw_signals": list(self.raw_signals),
            "unsupported_signals": dict(self.unsupported_signals),
        }


@dataclass(frozen=True)
class IntentEvidence:
    classifier_mode: ClassifierMode
    matched_rules: tuple[RuleMatch, ...] = ()
    raw_signals: tuple[str, ...] = ()
    signal_buckets: SignalBuckets = field(default_factory=SignalBuckets)
    unsupported_signals: dict[str, bool] = field(default_factory=dict)
    dependency_signals: dict[str, bool] = field(default_factory=dict)
    context_signals: ContextSignals = field(default_factory=ContextSignals)
    candidate_intents: tuple[CandidateIntent, ...] = ()
    task_candidates: tuple[TaskCandidate, ...] = ()
    model_result: ModelResult | None = None
    rule_confidence: RuleConfidence | None = None

    @property
    def meta(self) -> EvidenceMeta:
        return EvidenceMeta(
            classifier_mode=self.classifier_mode,
            matched_rules=self.matched_rules,
            rule_confidence=self.rule_confidence,
            model_result=self.model_result,
        )

    @property
    def intent_evidence(self) -> IntentEvidenceView:
        return IntentEvidenceView(
            raw_signals=self.signal_buckets.intent,
            candidate_intents=self.candidate_intents,
        )

    @property
    def task_evidence(self) -> TaskEvidenceView:
        return TaskEvidenceView(
            raw_signals=self.signal_buckets.task,
            task_candidates=self.task_candidates,
        )

    @property
    def context_evidence(self) -> ContextEvidenceView:
        return ContextEvidenceView(
            raw_signals=self.signal_buckets.context,
            dependency_signals=self.dependency_signals,
            context_signals=self.context_signals,
        )

    @property
    def safety_evidence(self) -> SafetyEvidenceView:
        return SafetyEvidenceView(
            raw_signals=self.signal_buckets.safety,
            unsupported_signals=self.unsupported_signals,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "classifier_mode": self.classifier_mode,
            "matched_rules": [item.to_dict() for item in self.matched_rules],
            "raw_signals": list(self.raw_signals),
            "signal_buckets": self.signal_buckets.to_dict(),
            "unsupported_signals": dict(self.unsupported_signals),
            "dependency_signals": dict(self.dependency_signals),
            "context_signals": self.context_signals.to_dict(),
            "candidate_intents": [item.to_dict() for item in self.candidate_intents],
            "task_candidates": [item.to_dict() for item in self.task_candidates],
            "model_result": self.model_result.to_dict() if self.model_result else None,
            "rule_confidence": self.rule_confidence.to_dict() if self.rule_confidence else None,
        }

    def to_v2_dict(self) -> dict[str, Any]:
        return {
            "classifier_mode": self.classifier_mode,
            "matched_rules": [item.to_dict() for item in self.matched_rules],
            "signal_buckets": self.signal_buckets.to_dict(),
            "unsupported_signals": dict(self.unsupported_signals),
            "context_signals": self.context_signals.to_dict(),
            "candidate_intents": [item.to_dict() for item in self.candidate_intents],
            "task_candidates": [item.to_dict() for item in self.task_candidates],
            "model_result": self.model_result.to_dict() if self.model_result else None,
            "rule_confidence": self.rule_confidence.to_dict() if self.rule_confidence else None,
        }

    def to_grouped_dict(self) -> dict[str, Any]:
        return {
            "meta": self.meta.to_dict(),
            "intent": self.intent_evidence.to_dict(),
            "task": self.task_evidence.to_dict(),
            "context": self.context_evidence.to_dict(),
            "safety": self.safety_evidence.to_dict(),
        }


@dataclass(frozen=True)
class ResolvedTask:
    complexity: TaskComplexity
    shape: TaskShape
    topology: TaskTopology = "single"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_v1_dict(self) -> dict[str, Any]:
        return {
            "complexity": self.complexity,
            "shape": self.shape,
            "needs_query_decomposition": self.complexity == "compound"
            and self.topology in {"parallel_queries", "parallel_subtasks"},
            "needs_agent_planning": self.complexity == "complex",
        }


@dataclass(frozen=True)
class DecisionTrace:
    strength: Strength
    source: DecisionSource
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ResolvedIntentView:
    main_intent: MainIntent
    modifiers: IntentModifiers = field(default_factory=IntentModifiers)

    def to_dict(self) -> dict[str, Any]:
        return {
            "main_intent": self.main_intent,
            "modifiers": self.modifiers.to_dict(),
        }


@dataclass(frozen=True)
class ResolvedContext:
    dependency: ContextDependency = "none"

    def to_dict(self) -> dict[str, Any]:
        return {"dependency": self.dependency}


@dataclass(frozen=True)
class ResolvedIntent:
    main_intent: MainIntent
    modifiers: IntentModifiers = field(default_factory=IntentModifiers)
    task: ResolvedTask = field(
        default_factory=lambda: ResolvedTask(complexity="simple", shape="none")
    )
    context_dependency: ContextDependency = "none"
    decision: DecisionTrace = field(
        default_factory=lambda: DecisionTrace(
            strength="low",
            source="fallback",
            reason="No decision trace.",
        )
    )

    @property
    def intent(self) -> ResolvedIntentView:
        return ResolvedIntentView(main_intent=self.main_intent, modifiers=self.modifiers)

    @property
    def context(self) -> ResolvedContext:
        return ResolvedContext(dependency=self.context_dependency)

    def to_dict(self) -> dict[str, Any]:
        return {
            "main_intent": self.main_intent,
            "modifiers": self.modifiers.to_dict(),
            "task": self.task.to_dict(),
            "context_dependency": self.context_dependency,
            "decision": self.decision.to_dict(),
        }

    def to_v1_dict(self) -> dict[str, Any]:
        return {
            "main_intent": self.main_intent,
            "modifiers": self.modifiers.to_dict(),
            "task": self.task.to_v1_dict(),
            "context_dependency": self.context_dependency,
            "decision": self.decision.to_dict(),
        }

    def to_grouped_dict(self) -> dict[str, Any]:
        return {
            "intent": self.intent.to_dict(),
            "task": self.task.to_dict(),
            "context": self.context.to_dict(),
            "decision": self.decision.to_dict(),
        }


@dataclass(frozen=True)
class ControlDispatch:
    route: Route
    mode: Mode = "normal"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ControlPolicy:
    rewrite: bool = False
    force_citation: bool = False
    use_planner: bool = False
    decompose_query: bool = False
    planning_level: PlanningLevel = "none"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ControlSignal:
    route: Route
    mode: Mode = "normal"
    rewrite: bool = False
    force_citation: bool = False
    use_planner: bool = False
    decompose_query: bool = False
    planning_level: PlanningLevel = "none"

    @property
    def dispatch(self) -> ControlDispatch:
        return ControlDispatch(route=self.route, mode=self.mode)

    @property
    def policy(self) -> ControlPolicy:
        return ControlPolicy(
            rewrite=self.rewrite,
            force_citation=self.force_citation,
            use_planner=self.use_planner,
            decompose_query=self.decompose_query,
            planning_level=self.planning_level,
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_grouped_dict(self) -> dict[str, Any]:
        return {
            "dispatch": self.dispatch.to_dict(),
            "policy": self.policy.to_dict(),
        }


@dataclass(frozen=True)
class IntentAnalysis:
    input: IntentInput
    evidence: IntentEvidence
    resolved: ResolvedIntent
    control: ControlSignal

    @property
    def main_intent(self) -> MainIntent:
        return self.resolved.main_intent

    @property
    def modifiers(self) -> IntentModifiers:
        return self.resolved.modifiers

    def to_dict(self) -> dict[str, Any]:
        return {
            "input": self.input.to_dict(),
            "evidence": self.evidence.to_dict(),
            "resolved": self.resolved.to_dict(),
            "control": self.control.to_dict(),
        }

    def to_grouped_dict(self) -> dict[str, Any]:
        return {
            "input": self.input.to_dict(),
            "evidence": self.evidence.to_grouped_dict(),
            "resolved": self.resolved.to_grouped_dict(),
            "control": self.control.to_grouped_dict(),
        }
