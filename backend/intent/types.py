from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal


MainIntent = Literal["qa", "chat", "system", "unsupported"]
TaskComplexity = Literal["simple", "compound", "complex"]
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
    last_answer_summary: str = ""
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

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class IntentModifiers:
    follow_up: bool = False
    challenge: bool = False
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
class IntentEvidence:
    classifier_mode: ClassifierMode
    matched_rules: tuple[RuleMatch, ...] = ()
    raw_signals: tuple[str, ...] = ()
    unsupported_signals: dict[str, bool] = field(default_factory=dict)
    dependency_signals: dict[str, bool] = field(default_factory=dict)
    candidate_intents: tuple[CandidateIntent, ...] = ()
    task_candidates: tuple[TaskCandidate, ...] = ()
    model_result: ModelResult | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "classifier_mode": self.classifier_mode,
            "matched_rules": [item.to_dict() for item in self.matched_rules],
            "raw_signals": list(self.raw_signals),
            "unsupported_signals": dict(self.unsupported_signals),
            "dependency_signals": dict(self.dependency_signals),
            "candidate_intents": [item.to_dict() for item in self.candidate_intents],
            "task_candidates": [item.to_dict() for item in self.task_candidates],
            "model_result": self.model_result.to_dict() if self.model_result else None,
        }


@dataclass(frozen=True)
class ResolvedTask:
    complexity: TaskComplexity
    shape: TaskShape
    needs_query_decomposition: bool = False
    needs_agent_planning: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DecisionTrace:
    strength: Strength
    source: DecisionSource
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


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

    def to_dict(self) -> dict[str, Any]:
        return {
            "main_intent": self.main_intent,
            "modifiers": self.modifiers.to_dict(),
            "task": self.task.to_dict(),
            "context_dependency": self.context_dependency,
            "decision": self.decision.to_dict(),
        }


@dataclass(frozen=True)
class ControlSignal:
    route: Route
    mode: Mode = "normal"
    rewrite: bool = False
    force_citation: bool = False
    use_planner: bool = False
    decompose_query: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


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
