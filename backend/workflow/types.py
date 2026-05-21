from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

from intent.types import ControlTrace


WorkflowAction = Literal["respond", "agent", "knowledge_orchestrator", "reject"]
KnowledgeScopeStatus = Literal["resolved", "needs_clarification"]
PowerName = Literal[
    "retrieval_power",
    "context_binding_power",
    "planning_power",
    "challenge_power",
    "decomposition_power",
]
RetrievalMetricValue = Literal["good", "weak", "bad"]


@dataclass(frozen=True)
class WorkflowPolicyFlags:
    ask_clarification_first: bool = False
    need_planner: bool = False
    need_query_decomposition: bool = False
    need_context_binding: bool = False
    need_retrieval: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class WorkflowPlan:
    route: str
    handling_mode: str
    action: WorkflowAction
    use_context: bool
    cite_sources: bool
    use_planner: bool
    decompose_query: bool
    rewrite_query: bool
    should_ask_clarification_first: bool
    trace: ControlTrace
    enabled_powers: tuple[PowerName, ...] = ()
    knowledge_scope_status: KnowledgeScopeStatus = "resolved"
    policy_flags: WorkflowPolicyFlags = field(default_factory=WorkflowPolicyFlags)
    notes: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["trace"] = self.trace.to_dict()
        payload["notes"] = list(self.notes)
        payload["enabled_powers"] = list(self.enabled_powers)
        payload["policy_flags"] = self.policy_flags.to_dict()
        return payload


@dataclass(frozen=True)
class QueryUnit:
    unit_id: str
    text: str
    origin: Literal["primary", "repair", "support"] = "primary"
    target_refs: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "unit_id": self.unit_id,
            "text": self.text,
            "origin": self.origin,
            "target_refs": list(self.target_refs),
        }


@dataclass(frozen=True)
class EvidenceItem:
    evidence_id: str
    source_path: str
    source_type: str
    locator: str
    snippet: str
    channel: str
    score: float | None = None
    query_unit_ids: tuple[str, ...] = ()
    parent_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "evidence_id": self.evidence_id,
            "source_path": self.source_path,
            "source_type": self.source_type,
            "locator": self.locator,
            "snippet": self.snippet,
            "channel": self.channel,
            "score": self.score,
            "query_unit_ids": list(self.query_unit_ids),
            "parent_id": self.parent_id,
        }


@dataclass(frozen=True)
class RetrievalQualityAssessment:
    hit_count_score: RetrievalMetricValue
    dedup_hit_score: RetrievalMetricValue
    target_overlap_score: RetrievalMetricValue
    coverage_score: RetrievalMetricValue
    non_empty_snippet_score: RetrievalMetricValue
    source_quality_score: RetrievalMetricValue
    weighted_score: float
    status: RetrievalMetricValue
    should_repair: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class EvidenceBundle:
    query_unit_results: tuple[dict[str, Any], ...] = ()
    merged_evidence_items: tuple[EvidenceItem, ...] = ()
    source_refs: tuple[str, ...] = ()
    coverage_summary: dict[str, Any] = field(default_factory=dict)
    quality_summary: dict[str, Any] = field(default_factory=dict)
    missing_evidence_notes: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "query_unit_results": [dict(item) for item in self.query_unit_results],
            "merged_evidence_items": [item.to_dict() for item in self.merged_evidence_items],
            "source_refs": list(self.source_refs),
            "coverage_summary": dict(self.coverage_summary),
            "quality_summary": dict(self.quality_summary),
            "missing_evidence_notes": list(self.missing_evidence_notes),
        }


@dataclass(frozen=True)
class ChallengeResult:
    status: str
    targets: tuple[dict[str, Any], ...] = ()
    evidence_assessment: dict[str, Any] = field(default_factory=dict)
    review_findings: tuple[dict[str, Any], ...] = ()
    answer_constraints: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "targets": [dict(item) for item in self.targets],
            "evidence_assessment": dict(self.evidence_assessment),
            "review_findings": [dict(item) for item in self.review_findings],
            "answer_constraints": dict(self.answer_constraints),
        }


@dataclass(frozen=True)
class ExecutionPayload:
    route: str
    handling_mode: str
    action: WorkflowAction
    status: Literal["ready", "needs_clarification", "rejected"] = "ready"
    enabled_powers: tuple[PowerName, ...] = ()
    instructions: tuple[str, ...] = ()
    knowledge_scope_status: KnowledgeScopeStatus = "resolved"
    context_bundle: dict[str, Any] = field(default_factory=dict)
    evidence_bundle: EvidenceBundle | None = None
    plan_bundle: dict[str, Any] = field(default_factory=dict)
    review_bundle: dict[str, Any] = field(default_factory=dict)
    answer_constraints: dict[str, Any] = field(default_factory=dict)
    notes: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "route": self.route,
            "handling_mode": self.handling_mode,
            "action": self.action,
            "status": self.status,
            "enabled_powers": list(self.enabled_powers),
            "instructions": list(self.instructions),
            "knowledge_scope_status": self.knowledge_scope_status,
            "context_bundle": dict(self.context_bundle),
            "evidence_bundle": self.evidence_bundle.to_dict() if self.evidence_bundle else None,
            "plan_bundle": dict(self.plan_bundle),
            "review_bundle": dict(self.review_bundle),
            "answer_constraints": dict(self.answer_constraints),
            "notes": list(self.notes),
        }
