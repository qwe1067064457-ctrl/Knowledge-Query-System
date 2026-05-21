from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

from intent.schema.intent_types import ControlTrace


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
        quality_summary = dict(self.quality_summary)
        coverage_summary = dict(self.coverage_summary)
        status = str(quality_summary.get("status") or self._derive_summary_status())
        evidence_summary = {
            "query_unit_count": len(self.query_unit_results),
            "merged_evidence_count": len(self.merged_evidence_items),
            "source_ref_count": len(self.source_refs),
            "retrieval_quality_status": status,
            "repairable_units": int(quality_summary.get("repairable_units", 0)),
            "repaired_units": int(quality_summary.get("repaired_units", 0)),
            "missing_evidence": bool(self.missing_evidence_notes),
            "coverage_query_units": int(coverage_summary.get("query_units", len(self.query_unit_results))),
            "coverage_sources": int(coverage_summary.get("sources", len(self.source_refs))),
        }
        return {
            "query_unit_results": [dict(item) for item in self.query_unit_results],
            "merged_evidence_items": [item.to_dict() for item in self.merged_evidence_items],
            "source_refs": list(self.source_refs),
            "coverage_summary": coverage_summary,
            "quality_summary": quality_summary,
            "evidence_summary": evidence_summary,
            "missing_evidence_notes": list(self.missing_evidence_notes),
        }

    def _derive_summary_status(self) -> str:
        average_score = float(self.quality_summary.get("average_weighted_score", 0.0) or 0.0)
        if average_score >= 0.75:
            return "good"
        if average_score >= 0.45:
            return "weak"
        return "bad"


@dataclass(frozen=True)
class ContextBundleSummaryView:
    binding_summary: str = "not_applicable"
    candidate_count: int = 0
    query_unit_count: int = 0


@dataclass(frozen=True)
class PlanBundleSummaryView:
    planning_mode: str = "not_applicable"
    step_count: int = 0
    checkpoint_count: int = 0
    comparison_unit_count: int = 0
    bound_target_ref_count: int = 0
    refined: bool = False
    fallback_used: bool = False


@dataclass(frozen=True)
class ReviewBundleSummaryView:
    review_mode: str = "not_applicable"
    review_confidence: str = "not_applicable"
    review_scope: str = "not_applicable"
    status_summary: str = "not_applicable"
    target_count: int = 0
    matched_target_count: int = 0
    needs_more_evidence_target_count: int = 0
    follow_up_retrieval_attempted: bool = False
    follow_up_retrieval_improved: bool = False


@dataclass(frozen=True)
class EvidenceBundleSummaryView:
    retrieval_quality_status: str = "not_applicable"
    query_unit_count: int = 0
    merged_evidence_count: int = 0
    source_ref_count: int = 0
    repaired_units: int = 0
    missing_evidence: bool = False


@dataclass(frozen=True)
class ContextBindingResult:
    bound_targets: tuple[dict[str, Any], ...] = ()
    bound_evidence: tuple[dict[str, Any], ...] = ()
    comparison_set: tuple[dict[str, Any], ...] = ()
    binding_confidence: str = "low"
    binding_ambiguous: bool = False
    matched_by: str | None = None
    clarification_hint: str | None = None
    binding_summary: str | None = None
    notes: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "bound_targets": [dict(item) for item in self.bound_targets],
            "bound_evidence": [dict(item) for item in self.bound_evidence],
            "comparison_set": [dict(item) for item in self.comparison_set],
            "binding_confidence": self.binding_confidence,
            "binding_ambiguous": self.binding_ambiguous,
            "matched_by": self.matched_by,
            "clarification_hint": self.clarification_hint,
            "binding_summary": self.binding_summary,
            "notes": list(self.notes),
        }

    def target_refs(self) -> tuple[str, ...]:
        refs: list[str] = []
        for item in self.bound_targets:
            ref = str(item.get("object_id") or item.get("content") or "").strip()
            if ref:
                refs.append(ref)
        return tuple(refs)

    @classmethod
    def from_dict(cls, payload: dict[str, Any] | None) -> "ContextBindingResult":
        data = dict(payload or {})
        return cls(
            bound_targets=tuple(dict(item) for item in data.get("bound_targets", ()) or ()),
            bound_evidence=tuple(dict(item) for item in data.get("bound_evidence", ()) or ()),
            comparison_set=tuple(dict(item) for item in data.get("comparison_set", ()) or ()),
            binding_confidence=str(data.get("binding_confidence", "low")),
            binding_ambiguous=bool(data.get("binding_ambiguous", False)),
            matched_by=data.get("matched_by"),
            clarification_hint=data.get("clarification_hint"),
            binding_summary=data.get("binding_summary"),
            notes=tuple(str(item) for item in data.get("notes", ()) or ()),
        )


@dataclass(frozen=True)
class ContextBundle:
    trace: dict[str, Any] = field(default_factory=dict)
    binding: ContextBindingResult | dict[str, Any] | None = None
    binding_summary: str = "not_applicable"
    candidate_count: int = 0
    query_units: tuple[dict[str, Any], ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "trace": dict(self.trace),
            "binding": None if self.binding is None else self.binding_obj().to_dict(),
            "binding_summary": self.binding_summary,
            "candidate_count": self.candidate_count,
            "query_units": [dict(item) for item in self.query_units],
        }

    def binding_obj(self) -> ContextBindingResult:
        if isinstance(self.binding, ContextBindingResult):
            return self.binding
        return ContextBindingResult.from_dict(dict(self.binding or {}))

    def bound_targets(self) -> tuple[dict[str, Any], ...]:
        if self.binding is None:
            return ()
        return self.binding_obj().bound_targets

    @classmethod
    def from_dict(
        cls,
        payload: dict[str, Any] | None,
        *,
        default_trace: dict[str, Any] | None = None,
    ) -> "ContextBundle":
        data = dict(payload or {})
        binding_payload = data.get("binding")
        if binding_payload is None:
            binding = None
        elif isinstance(binding_payload, ContextBindingResult):
            binding = binding_payload
        else:
            binding = ContextBindingResult.from_dict(dict(binding_payload))
        return cls(
            trace=dict(data.get("trace", default_trace or {})),
            binding=binding,
            binding_summary=str(data.get("binding_summary", "not_applicable")),
            candidate_count=int(data.get("candidate_count", 0) or 0),
            query_units=tuple(dict(item) for item in data.get("query_units", ()) or ()),
        )


@dataclass(frozen=True)
class PlanBundle:
    goal: str = ""
    task_shape: str = "not_applicable"
    task_topology: str = "not_applicable"
    planning_mode: str = "not_applicable"
    query_units: tuple[dict[str, Any], ...] = ()
    ordered_steps: tuple[dict[str, Any], ...] = ()
    comparison_units: tuple[dict[str, Any], ...] = ()
    execution_checkpoints: tuple[dict[str, Any], ...] = ()
    bound_target_refs: tuple[str, ...] = ()
    format_helper_applied: bool = False
    refined: bool = False
    fallback_used: bool = False
    fallback_reason: tuple[str, ...] = ()

    def summary_dict(self) -> dict[str, Any]:
        return {
            "planning_mode": self.planning_mode,
            "step_count": len(self.ordered_steps),
            "checkpoint_count": len(self.execution_checkpoints),
            "comparison_unit_count": len(self.comparison_units),
            "bound_target_ref_count": len(self.bound_target_refs),
            "refined": self.refined,
            "fallback_used": self.fallback_used,
            "fallback_reason": list(self.fallback_reason),
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "goal": self.goal,
            "task_shape": self.task_shape,
            "task_topology": self.task_topology,
            "planning_mode": self.planning_mode,
            "query_units": [dict(item) for item in self.query_units],
            "ordered_steps": [dict(item) for item in self.ordered_steps],
            "comparison_units": [dict(item) for item in self.comparison_units],
            "execution_checkpoints": [dict(item) for item in self.execution_checkpoints],
            "bound_target_refs": list(self.bound_target_refs),
            "format_helper_applied": self.format_helper_applied,
            "refined": self.refined,
            "fallback_used": self.fallback_used,
            "fallback_reason": list(self.fallback_reason),
            "plan_summary": self.summary_dict(),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any] | None) -> "PlanBundle":
        data = dict(payload or {})
        summary = dict(data.get("plan_summary", {}))
        return cls(
            goal=str(data.get("goal", "")),
            task_shape=str(data.get("task_shape", "not_applicable")),
            task_topology=str(data.get("task_topology", "not_applicable")),
            planning_mode=str(data.get("planning_mode", summary.get("planning_mode", "not_applicable"))),
            query_units=tuple(dict(item) for item in data.get("query_units", ()) or ()),
            ordered_steps=tuple(dict(item) for item in data.get("ordered_steps", ()) or ()),
            comparison_units=tuple(dict(item) for item in data.get("comparison_units", ()) or ()),
            execution_checkpoints=tuple(dict(item) for item in data.get("execution_checkpoints", ()) or ()),
            bound_target_refs=tuple(str(item) for item in data.get("bound_target_refs", ()) or ()),
            format_helper_applied=bool(data.get("format_helper_applied", False)),
            refined=bool(data.get("refined", summary.get("refined", False))),
            fallback_used=bool(data.get("fallback_used", summary.get("fallback_used", False))),
            fallback_reason=tuple(str(item) for item in data.get("fallback_reason", summary.get("fallback_reason", ())) or ()),
        )


@dataclass(frozen=True)
class ReviewBundle:
    review_mode: str = "not_applicable"
    review_confidence: str = "not_applicable"
    review_scope: str = "not_applicable"
    status: str = "not_applicable"
    targets: tuple[dict[str, Any], ...] = ()
    evidence_assessment: dict[str, Any] = field(default_factory=dict)
    review_findings: tuple[dict[str, Any], ...] = ()
    review_summary: dict[str, Any] = field(default_factory=dict)

    def _normalized_summary(self) -> dict[str, Any]:
        defaults = {
            "target_count": len(self.targets),
            "matched_target_count": 0,
            "matched_target_refs": [],
            "unsupported_target_refs": [],
            "needs_more_evidence_targets": [],
            "status_summary": self.status,
            "review_mode": self.review_mode,
            "review_confidence": self.review_confidence,
            "review_scope": self.review_scope,
            "follow_up_retrieval_attempted": False,
            "follow_up_retrieval_improved": False,
            "follow_up_retrieval_sources": [],
            "follow_up_retrieval_retrieved_evidence_count": 0,
        }
        summary = dict(self.review_summary)
        defaults.update(summary)
        defaults["matched_target_refs"] = list(defaults.get("matched_target_refs", ()))
        defaults["unsupported_target_refs"] = list(defaults.get("unsupported_target_refs", ()))
        defaults["needs_more_evidence_targets"] = list(defaults.get("needs_more_evidence_targets", ()))
        defaults["follow_up_retrieval_sources"] = list(defaults.get("follow_up_retrieval_sources", ()))
        return defaults

    def to_dict(self) -> dict[str, Any]:
        return {
            "review_mode": self.review_mode,
            "review_confidence": self.review_confidence,
            "review_scope": self.review_scope,
            "status": self.status,
            "targets": [dict(item) for item in self.targets],
            "evidence_assessment": dict(self.evidence_assessment),
            "review_findings": [dict(item) for item in self.review_findings],
            "review_summary": self._normalized_summary(),
        }

    def summary_obj(self) -> dict[str, Any]:
        return self._normalized_summary()

    def matched_target_refs(self) -> tuple[str, ...]:
        summary = self._normalized_summary()
        return tuple(str(item) for item in summary.get("matched_target_refs", ()) if item)

    def unsupported_target_refs(self) -> tuple[str, ...]:
        summary = self._normalized_summary()
        return tuple(str(item) for item in summary.get("unsupported_target_refs", ()) if item)

    def needs_more_evidence_targets(self) -> tuple[str, ...]:
        summary = self._normalized_summary()
        return tuple(str(item) for item in summary.get("needs_more_evidence_targets", ()) if item)

    @classmethod
    def from_dict(cls, payload: dict[str, Any] | None) -> "ReviewBundle":
        data = dict(payload or {})
        review_mode = str(data.get("review_mode", "not_applicable"))
        review_confidence = str(data.get("review_confidence", "not_applicable"))
        review_scope = str(data.get("review_scope", "not_applicable"))
        status = str(data.get("status", "not_applicable"))
        summary = dict(data.get("review_summary", {}))
        summary.setdefault("status_summary", status)
        summary.setdefault("review_mode", review_mode)
        summary.setdefault("review_confidence", review_confidence)
        summary.setdefault("review_scope", review_scope)
        summary.setdefault("target_count", len(tuple(data.get("targets", ()) or ())))
        return cls(
            review_mode=review_mode,
            review_confidence=review_confidence,
            review_scope=review_scope,
            status=status,
            targets=tuple(dict(item) for item in data.get("targets", ()) or ()),
            evidence_assessment=dict(data.get("evidence_assessment", {})),
            review_findings=tuple(dict(item) for item in data.get("review_findings", ()) or ()),
            review_summary=summary,
        )


@dataclass(frozen=True)
class ChallengeResult:
    status: str
    targets: tuple[dict[str, Any], ...] = ()
    evidence_assessment: dict[str, Any] = field(default_factory=dict)
    review_findings: tuple[dict[str, Any], ...] = ()
    answer_constraints: dict[str, Any] = field(default_factory=dict)
    review_summary: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        review_summary = dict(self.review_summary)
        follow_up_retrieval = dict(self.evidence_assessment.get("follow_up_retrieval", {}))
        target_count = len(self.targets)
        review_scope = "multi_target" if target_count > 1 else "single_target" if target_count == 1 else "not_applicable"
        review_mode = "challenge_review" if self.status != "not_applicable" else "not_applicable"
        review_confidence = self._derive_review_confidence(
            status=self.status,
            evidence_assessment=self.evidence_assessment,
            follow_up_retrieval=follow_up_retrieval,
        )
        if not review_summary:
            matched_target_refs = [
                str(item.get("target_ref"))
                for item in self.review_findings
                if item.get("judgment") == "supported"
            ]
            unsupported_target_refs = [
                str(item.get("target_ref"))
                for item in self.review_findings
                if item.get("judgment") != "supported"
            ]
            matched_target_count = int(self.evidence_assessment.get("matched_target_count", len(matched_target_refs)))
            review_summary = {
                "target_count": target_count,
                "matched_target_count": matched_target_count,
                "matched_target_refs": matched_target_refs,
                "unsupported_target_refs": unsupported_target_refs,
                "needs_more_evidence_targets": unsupported_target_refs,
                "status_summary": self.status,
                "review_mode": review_mode,
                "review_confidence": review_confidence,
                "review_scope": review_scope,
                "follow_up_retrieval_attempted": bool(follow_up_retrieval.get("attempted")),
                "follow_up_retrieval_improved": bool(follow_up_retrieval.get("improved")),
                "follow_up_retrieval_sources": list(follow_up_retrieval.get("source_refs", ())),
                "follow_up_retrieval_retrieved_evidence_count": int(follow_up_retrieval.get("retrieved_evidence_count", 0)),
            }
        else:
            review_summary.setdefault("target_count", target_count)
            review_summary.setdefault(
                "matched_target_count",
                int(self.evidence_assessment.get("matched_target_count", len(review_summary.get("matched_target_refs", ())))),
            )
            review_summary.setdefault(
                "matched_target_refs",
                [
                    str(item.get("target_ref"))
                    for item in self.review_findings
                    if item.get("judgment") == "supported"
                ],
            )
            review_summary.setdefault(
                "unsupported_target_refs",
                [
                    str(item.get("target_ref"))
                    for item in self.review_findings
                    if item.get("judgment") != "supported"
                ],
            )
            review_summary.setdefault(
                "needs_more_evidence_targets",
                list(self.evidence_assessment.get("needs_more_evidence_targets", review_summary.get("unsupported_target_refs", ()))),
            )
            review_summary.setdefault("status_summary", self.status)
            review_summary.setdefault("review_mode", review_mode)
            review_summary.setdefault("review_confidence", review_confidence)
            review_summary.setdefault("review_scope", review_scope)
            review_summary.setdefault("follow_up_retrieval_attempted", bool(follow_up_retrieval.get("attempted")))
            review_summary.setdefault("follow_up_retrieval_improved", bool(follow_up_retrieval.get("improved")))
            review_summary.setdefault("follow_up_retrieval_sources", list(follow_up_retrieval.get("source_refs", ())))
            review_summary.setdefault(
                "follow_up_retrieval_retrieved_evidence_count",
                int(follow_up_retrieval.get("retrieved_evidence_count", 0)),
            )
        return {
            "review_mode": review_summary.get("review_mode", review_mode),
            "review_confidence": review_summary.get("review_confidence", review_confidence),
            "review_scope": review_summary.get("review_scope", review_scope),
            "status": self.status,
            "targets": [dict(item) for item in self.targets],
            "evidence_assessment": dict(self.evidence_assessment),
            "review_findings": [dict(item) for item in self.review_findings],
            "answer_constraints": dict(self.answer_constraints),
            "review_summary": review_summary,
        }

    def to_review_bundle(self) -> ReviewBundle:
        payload = self.to_dict()
        return ReviewBundle.from_dict(payload)

    @staticmethod
    def _derive_review_confidence(
        *,
        status: str,
        evidence_assessment: dict[str, Any],
        follow_up_retrieval: dict[str, Any],
    ) -> str:
        if status == "not_applicable":
            return "not_applicable"
        if status == "needs_clarification":
            return "low"
        if status == "insufficient_evidence":
            return "low"
        if status == "partial_success":
            return "medium"
        if status == "success":
            if bool(follow_up_retrieval.get("attempted")):
                return "medium"
            if bool(evidence_assessment.get("sufficient")):
                return "high"
        return "medium"


@dataclass(frozen=True)
class ExecutionPayload:
    route: str
    handling_mode: str
    action: WorkflowAction
    status: Literal["ready", "needs_clarification", "rejected"] = "ready"
    enabled_powers: tuple[PowerName, ...] = ()
    instructions: tuple[str, ...] = ()
    knowledge_scope_status: KnowledgeScopeStatus = "resolved"
    context_bundle: ContextBundle | dict[str, Any] = field(default_factory=dict)
    evidence_bundle: EvidenceBundle | None = None
    plan_bundle: PlanBundle | dict[str, Any] = field(default_factory=dict)
    review_bundle: ReviewBundle | dict[str, Any] = field(default_factory=dict)
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
            "context_bundle": self.context_bundle_obj().to_dict(),
            "evidence_bundle": self.evidence_bundle.to_dict() if self.evidence_bundle else None,
            "plan_bundle": self.plan_bundle_obj().to_dict(),
            "review_bundle": self.review_bundle_obj().to_dict(),
            "answer_constraints": dict(self.answer_constraints),
            "notes": list(self.notes),
        }

    def context_bundle_obj(self) -> ContextBundle:
        if isinstance(self.context_bundle, ContextBundle):
            return self.context_bundle
        return ContextBundle.from_dict(dict(self.context_bundle or {}))

    def plan_bundle_obj(self) -> PlanBundle:
        if isinstance(self.plan_bundle, PlanBundle):
            return self.plan_bundle
        return PlanBundle.from_dict(dict(self.plan_bundle or {}))

    def review_bundle_obj(self) -> ReviewBundle:
        if isinstance(self.review_bundle, ReviewBundle):
            return self.review_bundle
        return ReviewBundle.from_dict(dict(self.review_bundle or {}))

    def context_summary_view(self) -> ContextBundleSummaryView:
        bundle = self.context_bundle_obj().to_dict()
        return ContextBundleSummaryView(
            binding_summary=str(bundle.get("binding_summary", "not_applicable")),
            candidate_count=int(bundle.get("candidate_count", 0) or 0),
            query_unit_count=len(list(bundle.get("query_units", ()))),
        )

    def plan_summary_view(self) -> PlanBundleSummaryView:
        summary = dict(self.plan_bundle_obj().to_dict().get("plan_summary", {}))
        return PlanBundleSummaryView(
            planning_mode=str(summary.get("planning_mode", "not_applicable")),
            step_count=int(summary.get("step_count", 0) or 0),
            checkpoint_count=int(summary.get("checkpoint_count", 0) or 0),
            comparison_unit_count=int(summary.get("comparison_unit_count", 0) or 0),
            bound_target_ref_count=int(summary.get("bound_target_ref_count", 0) or 0),
            refined=bool(summary.get("refined", False)),
            fallback_used=bool(summary.get("fallback_used", False)),
        )

    def review_summary_view(self) -> ReviewBundleSummaryView:
        review_bundle = self.review_bundle_obj().to_dict()
        summary = dict(review_bundle.get("review_summary", {}))
        return ReviewBundleSummaryView(
            review_mode=str(review_bundle.get("review_mode", summary.get("review_mode", "not_applicable"))),
            review_confidence=str(review_bundle.get("review_confidence", summary.get("review_confidence", "not_applicable"))),
            review_scope=str(review_bundle.get("review_scope", summary.get("review_scope", "not_applicable"))),
            status_summary=str(summary.get("status_summary", "not_applicable")),
            target_count=int(summary.get("target_count", 0) or 0),
            matched_target_count=int(summary.get("matched_target_count", 0) or 0),
            needs_more_evidence_target_count=len(list(summary.get("needs_more_evidence_targets", ()))),
            follow_up_retrieval_attempted=bool(summary.get("follow_up_retrieval_attempted", False)),
            follow_up_retrieval_improved=bool(summary.get("follow_up_retrieval_improved", False)),
        )

    def evidence_summary_view(self) -> EvidenceBundleSummaryView:
        summary = {}
        if self.evidence_bundle is not None:
            summary = dict(self.evidence_bundle.to_dict().get("evidence_summary", {}))
        return EvidenceBundleSummaryView(
            retrieval_quality_status=str(summary.get("retrieval_quality_status", "not_applicable")),
            query_unit_count=int(summary.get("query_unit_count", 0) or 0),
            merged_evidence_count=int(summary.get("merged_evidence_count", 0) or 0),
            source_ref_count=int(summary.get("source_ref_count", 0) or 0),
            repaired_units=int(summary.get("repaired_units", 0) or 0),
            missing_evidence=bool(summary.get("missing_evidence", False)),
        )
