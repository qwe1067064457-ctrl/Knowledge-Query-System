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
class EvidenceAssessmentResult:
    sufficient: bool = False
    partially_sufficient: bool = False
    used_existing_evidence: bool = False
    triggered_additional_retrieval: bool = False
    matched_target_count: int = 0
    target_count: int = 0
    coverage_ratio: float = 0.0
    supporting_evidence_refs: tuple[str, ...] = ()
    matched_target_refs: tuple[str, ...] = ()
    unsupported_target_refs: tuple[str, ...] = ()
    needs_more_evidence_targets: tuple[str, ...] = ()
    retrieve_if_needed: dict[str, Any] = field(default_factory=dict)
    per_target_assessment: tuple[dict[str, Any], ...] = ()
    per_target_support_counts: tuple[dict[str, Any], ...] = ()
    evidence_notes: tuple[str, ...] = ()
    follow_up_retrieval: dict[str, Any] = field(default_factory=dict)
    target_coverage: float = 0.0
    target_evidence_ref_overlap: float = 0.0
    missing_target_ratio: float = 0.0
    source_count: int = 0
    source_diversity: int = 0
    source_type_quality_band: str = "unknown"
    channel_quality_band: str = "unknown"
    fallback: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "sufficient": self.sufficient,
            "partially_sufficient": self.partially_sufficient,
            "used_existing_evidence": self.used_existing_evidence,
            "triggered_additional_retrieval": self.triggered_additional_retrieval,
            "matched_target_count": self.matched_target_count,
            "target_count": self.target_count,
            "coverage_ratio": self.coverage_ratio,
            "supporting_evidence_refs": list(self.supporting_evidence_refs),
            "matched_target_refs": list(self.matched_target_refs),
            "unsupported_target_refs": list(self.unsupported_target_refs),
            "needs_more_evidence_targets": list(self.needs_more_evidence_targets),
            "retrieve_if_needed": dict(self.retrieve_if_needed),
            "per_target_assessment": [dict(item) for item in self.per_target_assessment],
            "per_target_support_counts": [dict(item) for item in self.per_target_support_counts],
            "evidence_notes": list(self.evidence_notes),
            "target_coverage": self.target_coverage,
            "target_evidence_ref_overlap": self.target_evidence_ref_overlap,
            "missing_target_ratio": self.missing_target_ratio,
            "source_count": self.source_count,
            "source_diversity": self.source_diversity,
            "source_type_quality_band": self.source_type_quality_band,
            "channel_quality_band": self.channel_quality_band,
        }
        if self.follow_up_retrieval:
            payload["follow_up_retrieval"] = dict(self.follow_up_retrieval)
        if self.fallback:
            payload["fallback"] = self.fallback
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, Any] | None) -> "EvidenceAssessmentResult":
        data = dict(payload or {})
        return cls(
            sufficient=bool(data.get("sufficient", False)),
            partially_sufficient=bool(data.get("partially_sufficient", False)),
            used_existing_evidence=bool(data.get("used_existing_evidence", False)),
            triggered_additional_retrieval=bool(data.get("triggered_additional_retrieval", False)),
            matched_target_count=int(data.get("matched_target_count", 0) or 0),
            target_count=int(data.get("target_count", 0) or 0),
            coverage_ratio=float(data.get("coverage_ratio", 0.0) or 0.0),
            supporting_evidence_refs=tuple(str(item) for item in data.get("supporting_evidence_refs", ()) if item),
            matched_target_refs=tuple(str(item) for item in data.get("matched_target_refs", ()) if item),
            unsupported_target_refs=tuple(str(item) for item in data.get("unsupported_target_refs", ()) if item),
            needs_more_evidence_targets=tuple(str(item) for item in data.get("needs_more_evidence_targets", ()) if item),
            retrieve_if_needed=dict(data.get("retrieve_if_needed", {})),
            per_target_assessment=tuple(dict(item) for item in data.get("per_target_assessment", ()) or ()),
            per_target_support_counts=tuple(dict(item) for item in data.get("per_target_support_counts", ()) or ()),
            evidence_notes=tuple(str(item) for item in data.get("evidence_notes", ()) if item),
            follow_up_retrieval=dict(data.get("follow_up_retrieval", {})),
            target_coverage=float(data.get("target_coverage", data.get("coverage_ratio", 0.0)) or 0.0),
            target_evidence_ref_overlap=float(data.get("target_evidence_ref_overlap", 0.0) or 0.0),
            missing_target_ratio=float(data.get("missing_target_ratio", 0.0) or 0.0),
            source_count=int(data.get("source_count", 0) or 0),
            source_diversity=int(data.get("source_diversity", 0) or 0),
            source_type_quality_band=str(data.get("source_type_quality_band", "unknown")),
            channel_quality_band=str(data.get("channel_quality_band", "unknown")),
            fallback=str(data["fallback"]) if data.get("fallback") else None,
        )

    def needs_follow_up_retrieval(self) -> bool:
        return bool(self.retrieve_if_needed.get("needed", False))

    def retrieve_target_refs(self) -> tuple[str, ...]:
        return tuple(str(item) for item in self.retrieve_if_needed.get("target_refs", ()) if item)

    def follow_up_attempted(self) -> bool:
        return bool(self.follow_up_retrieval.get("attempted", False))

    def follow_up_improved(self) -> bool:
        return bool(self.follow_up_retrieval.get("improved", False))

    def supporting_evidence_ref_list(self) -> list[str]:
        return list(self.supporting_evidence_refs)

    def matched_target_ref_list(self) -> list[str]:
        return list(self.matched_target_refs)

    def unsupported_target_ref_list(self) -> list[str]:
        return list(self.unsupported_target_refs)

    def needs_more_evidence_target_list(self) -> list[str]:
        return list(self.needs_more_evidence_targets)

    def unsupported_target_count(self) -> int:
        return len(self.unsupported_target_refs)

    def needs_more_evidence_target_count(self) -> int:
        return len(self.needs_more_evidence_targets)

    def has_target_coverage_state(self) -> bool:
        return any(
            (
                self.target_count > 0,
                self.matched_target_count > 0,
                bool(self.matched_target_refs),
                bool(self.unsupported_target_refs),
                bool(self.needs_more_evidence_targets),
                bool(self.retrieve_if_needed),
                bool(self.per_target_assessment),
            )
        )

    def summary_view(self) -> "EvidenceAssessmentSummaryView":
        return EvidenceAssessmentSummaryView(
            sufficient=self.sufficient,
            partially_sufficient=self.partially_sufficient,
            target_count=self.target_count,
            matched_target_count=self.matched_target_count,
            unsupported_target_count=self.unsupported_target_count(),
            needs_more_evidence_target_count=self.needs_more_evidence_target_count(),
            follow_up_retrieval_attempted=self.follow_up_attempted(),
            follow_up_retrieval_improved=self.follow_up_improved(),
            source_count=self.source_count,
            source_diversity=self.source_diversity,
            missing_target_ratio=self.missing_target_ratio,
        )

    def follow_up_retrieval_source_refs(self) -> tuple[str, ...]:
        return tuple(str(item) for item in self.follow_up_retrieval.get("source_refs", ()) if item)

    def follow_up_retrieval_retrieved_evidence_count(self) -> int:
        return int(self.follow_up_retrieval.get("retrieved_evidence_count", 0) or 0)

    def per_target_assessment_map(self) -> dict[str, dict[str, Any]]:
        return {
            str(item.get("target_ref")): dict(item)
            for item in self.per_target_assessment
            if item.get("target_ref")
        }

    def target_is_matched(self, target_ref: str) -> bool:
        assessment = self.per_target_assessment_map().get(str(target_ref), {})
        return bool(assessment.get("matched", False))

    def matched_evidence_refs_for(self, target_ref: str) -> list[str]:
        assessment = self.per_target_assessment_map().get(str(target_ref), {})
        return [str(item) for item in assessment.get("matched_evidence_refs", ()) if item]

    def with_fallback(self, fallback: str | None) -> "EvidenceAssessmentResult":
        return type(self)(
            sufficient=self.sufficient,
            partially_sufficient=self.partially_sufficient,
            used_existing_evidence=self.used_existing_evidence,
            triggered_additional_retrieval=self.triggered_additional_retrieval,
            matched_target_count=self.matched_target_count,
            target_count=self.target_count,
            coverage_ratio=self.coverage_ratio,
            supporting_evidence_refs=self.supporting_evidence_refs,
            matched_target_refs=self.matched_target_refs,
            unsupported_target_refs=self.unsupported_target_refs,
            needs_more_evidence_targets=self.needs_more_evidence_targets,
            retrieve_if_needed=dict(self.retrieve_if_needed),
            per_target_assessment=self.per_target_assessment,
            per_target_support_counts=self.per_target_support_counts,
            evidence_notes=self.evidence_notes,
            follow_up_retrieval=dict(self.follow_up_retrieval),
            target_coverage=self.target_coverage,
            target_evidence_ref_overlap=self.target_evidence_ref_overlap,
            missing_target_ratio=self.missing_target_ratio,
            source_count=self.source_count,
            source_diversity=self.source_diversity,
            source_type_quality_band=self.source_type_quality_band,
            channel_quality_band=self.channel_quality_band,
            fallback=fallback,
        )

    def with_follow_up_retrieval(
        self,
        *,
        follow_up_retrieval: dict[str, Any],
        triggered_additional_retrieval: bool = True,
    ) -> "EvidenceAssessmentResult":
        return type(self)(
            sufficient=self.sufficient,
            partially_sufficient=self.partially_sufficient,
            used_existing_evidence=self.used_existing_evidence,
            triggered_additional_retrieval=triggered_additional_retrieval,
            matched_target_count=self.matched_target_count,
            target_count=self.target_count,
            coverage_ratio=self.coverage_ratio,
            supporting_evidence_refs=self.supporting_evidence_refs,
            matched_target_refs=self.matched_target_refs,
            unsupported_target_refs=self.unsupported_target_refs,
            needs_more_evidence_targets=self.needs_more_evidence_targets,
            retrieve_if_needed=dict(self.retrieve_if_needed),
            per_target_assessment=self.per_target_assessment,
            per_target_support_counts=self.per_target_support_counts,
            evidence_notes=self.evidence_notes,
            follow_up_retrieval=dict(follow_up_retrieval),
            target_coverage=self.target_coverage,
            target_evidence_ref_overlap=self.target_evidence_ref_overlap,
            missing_target_ratio=self.missing_target_ratio,
            source_count=self.source_count,
            source_diversity=self.source_diversity,
            source_type_quality_band=self.source_type_quality_band,
            channel_quality_band=self.channel_quality_band,
            fallback=self.fallback,
        )

    def __getitem__(self, key: str) -> Any:
        return self.to_dict()[key]

    def get(self, key: str, default: Any = None) -> Any:
        return self.to_dict().get(key, default)


@dataclass(frozen=True)
class ReviewEvaluationResult:
    status: str
    review_findings: tuple[dict[str, Any], ...] = ()
    answer_constraints: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "review_findings": [dict(item) for item in self.review_findings],
            "answer_constraints": dict(self.answer_constraints),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any] | None) -> "ReviewEvaluationResult":
        data = dict(payload or {})
        return cls(
            status=str(data.get("status", "insufficient_evidence")),
            review_findings=tuple(dict(item) for item in data.get("review_findings", ()) or ()),
            answer_constraints=dict(data.get("answer_constraints", {})),
        )

    def __getitem__(self, key: str) -> Any:
        return self.to_dict()[key]

    def get(self, key: str, default: Any = None) -> Any:
        return self.to_dict().get(key, default)

    def with_answer_constraints(self, answer_constraints: dict[str, Any]) -> "ReviewEvaluationResult":
        return type(self)(
            status=self.status,
            review_findings=self.review_findings,
            answer_constraints=dict(answer_constraints),
        )


@dataclass(frozen=True)
class RetrievalUnitResult:
    unit_id: str
    query: str
    origin: str
    quality: dict[str, Any] = field(default_factory=dict)
    evidence_count: int = 0
    repair_plan: dict[str, Any] = field(default_factory=dict)
    repair_applied: bool = False
    repair_strategy: str = "none"
    selected_query: str = ""
    selected_mode: str = "raw"
    repaired_query: str | None = None
    repaired_mode: str | None = None
    pre_quality: dict[str, Any] = field(default_factory=dict)
    post_quality: dict[str, Any] = field(default_factory=dict)
    retrieval_status: str | None = None
    fallback_used: bool | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "unit_id": self.unit_id,
            "query": self.query,
            "origin": self.origin,
            "quality": dict(self.quality),
            "evidence_count": self.evidence_count,
            "repair_plan": dict(self.repair_plan),
            "repair_applied": self.repair_applied,
            "repair_strategy": self.repair_strategy,
            "selected_query": self.selected_query,
            "selected_mode": self.selected_mode,
            "repaired_query": self.repaired_query,
            "repaired_mode": self.repaired_mode,
            "pre_quality": dict(self.pre_quality),
            "post_quality": dict(self.post_quality),
        }
        if self.retrieval_status is not None:
            payload["retrieval_status"] = self.retrieval_status
        if self.fallback_used is not None:
            payload["fallback_used"] = self.fallback_used
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, Any] | None) -> "RetrievalUnitResult":
        data = dict(payload or {})
        return cls(
            unit_id=str(data.get("unit_id", "")),
            query=str(data.get("query", "")),
            origin=str(data.get("origin", "primary")),
            quality=dict(data.get("quality", {})),
            evidence_count=int(data.get("evidence_count", 0) or 0),
            repair_plan=dict(data.get("repair_plan", {})),
            repair_applied=bool(data.get("repair_applied", False)),
            repair_strategy=str(data.get("repair_strategy", "none")),
            selected_query=str(data.get("selected_query", "")),
            selected_mode=str(data.get("selected_mode", "raw")),
            repaired_query=str(data["repaired_query"]) if data.get("repaired_query") is not None else None,
            repaired_mode=str(data["repaired_mode"]) if data.get("repaired_mode") is not None else None,
            pre_quality=dict(data.get("pre_quality", {})),
            post_quality=dict(data.get("post_quality", {})),
            retrieval_status=str(data["retrieval_status"]) if data.get("retrieval_status") is not None else None,
            fallback_used=bool(data["fallback_used"]) if data.get("fallback_used") is not None else None,
        )

    def __getitem__(self, key: str) -> Any:
        return self.to_dict()[key]

    def get(self, key: str, default: Any = None) -> Any:
        return self.to_dict().get(key, default)

    def repair_enabled(self) -> bool:
        return bool(self.repair_plan.get("enabled", False))

    def quality_status(self) -> str:
        return str(self.quality.get("status", "not_applicable"))

    def should_repair(self) -> bool:
        return bool(self.quality.get("should_repair", False))

    def was_repaired(self) -> bool:
        return self.repair_applied

    def repair_strategy_name(self) -> str:
        return self.repair_strategy

    def selected_query_text(self) -> str:
        return self.selected_query

    def selected_mode_name(self) -> str:
        return self.selected_mode


@dataclass(frozen=True)
class EvidenceRefCandidate:
    object_id: str
    object_type: str = "evidence_ref"
    content: str = ""
    refs: tuple[str, ...] = ()
    source_type: str | None = None
    channel: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "object_id": self.object_id,
            "object_type": self.object_type,
            "content": self.content,
            "refs": list(self.refs),
        }
        if self.source_type is not None:
            payload["source_type"] = self.source_type
        if self.channel is not None:
            payload["channel"] = self.channel
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, Any] | None) -> "EvidenceRefCandidate":
        data = dict(payload or {})
        return cls(
            object_id=str(data.get("object_id", "")),
            object_type=str(data.get("object_type", "evidence_ref")),
            content=str(data.get("content", "")),
            refs=tuple(str(item) for item in data.get("refs", ()) if item),
            source_type=str(data["source_type"]) if data.get("source_type") is not None else None,
            channel=str(data["channel"]) if data.get("channel") is not None else None,
        )

    def all_refs(self) -> tuple[str, ...]:
        refs = [self.object_id, *self.refs]
        return tuple(str(item) for item in refs if item)

    def as_target_candidate(self) -> dict[str, Any]:
        return {
            "object_id": self.object_id,
            "object_type": self.object_type,
            "content": self.content,
            "refs": list(self.refs),
        }


@dataclass(frozen=True)
class EvidenceBundle:
    query_unit_results: tuple[RetrievalUnitResult | dict[str, Any], ...] = ()
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
            "query_unit_results": [item.to_dict() for item in self.query_unit_result_objs()],
            "merged_evidence_items": [item.to_dict() for item in self.merged_evidence_items],
            "source_refs": list(self.source_refs),
            "coverage_summary": coverage_summary,
            "quality_summary": quality_summary,
            "evidence_summary": evidence_summary,
            "missing_evidence_notes": list(self.missing_evidence_notes),
        }

    def summary_obj(self) -> dict[str, Any]:
        summary = self.summary_view()
        return {
            "query_unit_count": summary.query_unit_count,
            "merged_evidence_count": summary.merged_evidence_count,
            "source_ref_count": summary.source_ref_count,
            "retrieval_quality_status": summary.retrieval_quality_status,
            "repairable_units": summary.repairable_units,
            "repaired_units": summary.repaired_units,
            "missing_evidence": summary.missing_evidence,
            "coverage_query_units": summary.coverage_query_units,
            "coverage_sources": summary.coverage_sources,
        }

    def summary_view(self) -> "EvidenceBundleSummaryView":
        quality_summary = dict(self.quality_summary)
        coverage_summary = dict(self.coverage_summary)
        return EvidenceBundleSummaryView(
            retrieval_quality_status=str(quality_summary.get("status") or self._derive_summary_status()),
            query_unit_count=self.query_unit_count(),
            merged_evidence_count=self.merged_evidence_count(),
            source_ref_count=self.source_ref_count(),
            repairable_units=int(quality_summary.get("repairable_units", 0) or 0),
            repaired_units=int(quality_summary.get("repaired_units", 0) or 0),
            missing_evidence=bool(self.missing_evidence_notes),
            coverage_query_units=int(coverage_summary.get("query_units", self.query_unit_count()) or 0),
            coverage_sources=int(coverage_summary.get("sources", self.source_ref_count()) or 0),
        )

    def query_unit_count(self) -> int:
        return len(self.query_unit_results)

    def query_unit_result_objs(self) -> tuple[RetrievalUnitResult, ...]:
        results: list[RetrievalUnitResult] = []
        for item in self.query_unit_results:
            if isinstance(item, RetrievalUnitResult):
                results.append(item)
            else:
                results.append(RetrievalUnitResult.from_dict(item))
        return tuple(results)

    def merged_evidence_count(self) -> int:
        return len(self.merged_evidence_items)

    def source_ref_count(self) -> int:
        return len(self.source_refs)

    def source_ref_list(self) -> list[str]:
        return list(self.source_refs)

    def retrieval_quality_status(self) -> str:
        return self.summary_view().retrieval_quality_status

    def repairable_unit_count(self) -> int:
        return self.summary_view().repairable_units

    def repaired_unit_count(self) -> int:
        return self.summary_view().repaired_units

    def missing_evidence_flag(self) -> bool:
        return self.summary_view().missing_evidence

    def coverage_query_unit_count(self) -> int:
        return self.summary_view().coverage_query_units

    def coverage_source_count(self) -> int:
        return self.summary_view().coverage_sources

    def to_evidence_ref_candidate_objs(self) -> tuple[EvidenceRefCandidate, ...]:
        return tuple(
            EvidenceRefCandidate(
                object_id=str(item.evidence_id),
                object_type="evidence_ref",
                content=item.snippet,
                refs=tuple(
                    str(ref)
                    for ref in (item.evidence_id, item.parent_id, item.source_path, item.locator)
                    if ref
                ),
                source_type=item.source_type,
                channel=item.channel,
            )
            for item in self.merged_evidence_items
        )

    def to_evidence_ref_candidates(self) -> tuple[dict[str, Any], ...]:
        return tuple(item.to_dict() for item in self.to_evidence_ref_candidate_objs())

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
    repairable_units: int = 0
    repaired_units: int = 0
    missing_evidence: bool = False
    coverage_query_units: int = 0
    coverage_sources: int = 0


@dataclass(frozen=True)
class EvidenceAssessmentSummaryView:
    sufficient: bool = False
    partially_sufficient: bool = False
    target_count: int = 0
    matched_target_count: int = 0
    unsupported_target_count: int = 0
    needs_more_evidence_target_count: int = 0
    follow_up_retrieval_attempted: bool = False
    follow_up_retrieval_improved: bool = False
    source_count: int = 0
    source_diversity: int = 0
    missing_target_ratio: float = 0.0


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
    rewritten_query: str | None = None
    state_snapshot: dict[str, Any] | None = None

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
            "rewritten_query": self.rewritten_query,
            "state_snapshot": dict(self.state_snapshot or {}),
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
            rewritten_query=str(data["rewritten_query"]) if data.get("rewritten_query") is not None else None,
            state_snapshot=dict(data.get("state_snapshot", {})) or None,
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

    def query_unit_dicts(self) -> tuple[dict[str, Any], ...]:
        return tuple(dict(item) for item in self.query_units)

    def summary_view(self) -> "ContextBundleSummaryView":
        return ContextBundleSummaryView(
            binding_summary=self.binding_summary,
            candidate_count=self.candidate_count,
            query_unit_count=len(self.query_units),
        )

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
        summary = self.summary_view()
        return {
            "planning_mode": summary.planning_mode,
            "step_count": summary.step_count,
            "checkpoint_count": summary.checkpoint_count,
            "comparison_unit_count": summary.comparison_unit_count,
            "bound_target_ref_count": summary.bound_target_ref_count,
            "refined": summary.refined,
            "fallback_used": summary.fallback_used,
            "fallback_reason": list(self.fallback_reason),
        }

    def query_unit_dicts(self) -> tuple[dict[str, Any], ...]:
        return tuple(dict(item) for item in self.query_units)

    def summary_obj(self) -> dict[str, Any]:
        return self.summary_dict()

    def summary_view(self) -> "PlanBundleSummaryView":
        return PlanBundleSummaryView(
            planning_mode=self.planning_mode,
            step_count=len(self.ordered_steps),
            checkpoint_count=len(self.execution_checkpoints),
            comparison_unit_count=len(self.comparison_units),
            bound_target_ref_count=len(self.bound_target_refs),
            refined=self.refined,
            fallback_used=self.fallback_used,
        )

    def step_count(self) -> int:
        return len(self.ordered_steps)

    def checkpoint_count(self) -> int:
        return len(self.execution_checkpoints)

    def comparison_unit_count(self) -> int:
        return len(self.comparison_units)

    def bound_target_ref_count(self) -> int:
        return len(self.bound_target_refs)

    def is_refined(self) -> bool:
        return self.refined

    def is_fallback(self) -> bool:
        return self.fallback_used

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
    evidence_assessment: EvidenceAssessmentResult | dict[str, Any] = field(default_factory=dict)
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
            "evidence_assessment": self.evidence_assessment_obj().to_dict(),
            "review_findings": [dict(item) for item in self.review_findings],
            "review_summary": self.summary_obj(),
        }

    def evidence_assessment_obj(self) -> EvidenceAssessmentResult:
        if isinstance(self.evidence_assessment, EvidenceAssessmentResult):
            return self.evidence_assessment
        return EvidenceAssessmentResult.from_dict(dict(self.evidence_assessment or {}))

    @staticmethod
    def derive_review_confidence(
        *,
        status: str,
        evidence_assessment: EvidenceAssessmentResult,
    ) -> str:
        if status == "not_applicable":
            return "not_applicable"
        if status in {"needs_clarification", "insufficient_evidence"}:
            return "low"
        if status == "partial_success":
            return "medium"
        if status == "success":
            if evidence_assessment.follow_up_attempted():
                return "medium"
            if evidence_assessment.sufficient:
                return "high"
        return "medium"

    @classmethod
    def from_challenge_result(
        cls,
        *,
        status: str,
        targets: tuple[dict[str, Any], ...] = (),
        evidence_assessment: EvidenceAssessmentResult | dict[str, Any] | None = None,
        review_findings: tuple[dict[str, Any], ...] = (),
        review_summary: dict[str, Any] | None = None,
    ) -> "ReviewBundle":
        assessment = (
            evidence_assessment
            if isinstance(evidence_assessment, EvidenceAssessmentResult)
            else EvidenceAssessmentResult.from_dict(dict(evidence_assessment or {}))
        )
        assessment_summary = assessment.summary_view()
        target_count = len(targets) or assessment_summary.target_count
        review_scope = "multi_target" if target_count > 1 else "single_target" if target_count == 1 else "not_applicable"
        review_mode = "challenge_review" if status != "not_applicable" else "not_applicable"
        review_confidence = cls.derive_review_confidence(
            status=status,
            evidence_assessment=assessment,
        )
        matched_target_refs = assessment.matched_target_ref_list() or [
            str(item.get("target_ref"))
            for item in review_findings
            if item.get("judgment") == "supported"
        ]
        unsupported_target_refs = assessment.unsupported_target_ref_list() or [
            str(item.get("target_ref"))
            for item in review_findings
            if item.get("judgment") != "supported"
        ]
        summary = dict(review_summary or {})
        summary.setdefault("target_count", target_count)
        summary.setdefault(
            "matched_target_count",
            int(assessment_summary.matched_target_count or len(summary.get("matched_target_refs", ()) or matched_target_refs)),
        )
        summary.setdefault("matched_target_refs", matched_target_refs)
        summary.setdefault("unsupported_target_refs", unsupported_target_refs)
        summary.setdefault(
            "needs_more_evidence_targets",
            assessment.needs_more_evidence_target_list()
            or list(summary.get("unsupported_target_refs", ()) or unsupported_target_refs),
        )
        summary.setdefault("status_summary", status)
        summary.setdefault("review_mode", review_mode)
        summary.setdefault("review_confidence", review_confidence)
        summary.setdefault("review_scope", review_scope)
        summary.setdefault("follow_up_retrieval_attempted", assessment_summary.follow_up_retrieval_attempted)
        summary.setdefault("follow_up_retrieval_improved", assessment_summary.follow_up_retrieval_improved)
        summary.setdefault("follow_up_retrieval_sources", list(assessment.follow_up_retrieval_source_refs()))
        summary.setdefault(
            "follow_up_retrieval_retrieved_evidence_count",
            assessment.follow_up_retrieval_retrieved_evidence_count(),
        )
        return cls(
            review_mode=review_mode,
            review_confidence=review_confidence,
            review_scope=review_scope,
            status=status,
            targets=targets,
            evidence_assessment=assessment,
            review_findings=review_findings,
            review_summary=summary,
        )

    @classmethod
    def from_review_evaluation(
        cls,
        *,
        targets: tuple[dict[str, Any], ...] = (),
        evidence_assessment: EvidenceAssessmentResult | dict[str, Any] | None = None,
        evaluation: ReviewEvaluationResult | dict[str, Any] | None = None,
        review_summary: dict[str, Any] | None = None,
    ) -> "ReviewBundle":
        evaluation_result = (
            evaluation
            if isinstance(evaluation, ReviewEvaluationResult)
            else ReviewEvaluationResult.from_dict(dict(evaluation or {}))
        )
        return cls.from_challenge_result(
            status=evaluation_result.status,
            targets=targets,
            evidence_assessment=evidence_assessment,
            review_findings=evaluation_result.review_findings,
            review_summary=review_summary,
        )

    def summary_obj(self) -> dict[str, Any]:
        summary = self._normalized_summary()
        summary["target_count"] = self.target_count()
        summary["matched_target_count"] = self.matched_target_count()
        summary["matched_target_refs"] = list(self.matched_target_refs())
        summary["unsupported_target_refs"] = list(self.unsupported_target_refs())
        summary["needs_more_evidence_targets"] = list(self.needs_more_evidence_targets())
        summary["status_summary"] = self.status_summary()
        summary["review_mode"] = self.review_mode
        summary["review_confidence"] = self.review_confidence
        summary["review_scope"] = self.review_scope
        summary["follow_up_retrieval_attempted"] = self.follow_up_retrieval_attempted()
        summary["follow_up_retrieval_improved"] = self.follow_up_retrieval_improved()
        summary["follow_up_retrieval_sources"] = list(self.follow_up_retrieval_sources())
        summary["follow_up_retrieval_retrieved_evidence_count"] = (
            self.follow_up_retrieval_retrieved_evidence_count()
        )
        return summary

    def summary_view(self) -> "ReviewBundleSummaryView":
        summary = self._normalized_summary()
        assessment = self.evidence_assessment_obj()
        assessment_summary = assessment.summary_view()
        has_assessment_follow_up = assessment.follow_up_attempted() or bool(assessment.follow_up_retrieval)
        has_assessment_target_coverage = assessment.has_target_coverage_state()
        return ReviewBundleSummaryView(
            review_mode=self.review_mode,
            review_confidence=self.review_confidence,
            review_scope=self.review_scope,
            status_summary=str(summary.get("status_summary", "not_applicable")),
            target_count=(
                int(assessment_summary.target_count)
                if has_assessment_target_coverage
                else int(summary.get("target_count", len(self.targets)) or 0)
            ),
            matched_target_count=(
                int(assessment_summary.matched_target_count)
                if has_assessment_target_coverage
                else int(summary.get("matched_target_count", 0) or 0)
            ),
            needs_more_evidence_target_count=int(
                assessment_summary.needs_more_evidence_target_count
                if has_assessment_target_coverage
                else len(list(summary.get("needs_more_evidence_targets", ())))
            ),
            follow_up_retrieval_attempted=(
                assessment_summary.follow_up_retrieval_attempted
                if has_assessment_follow_up
                else bool(summary.get("follow_up_retrieval_attempted", False))
            ),
            follow_up_retrieval_improved=(
                assessment_summary.follow_up_retrieval_improved
                if has_assessment_follow_up
                else bool(summary.get("follow_up_retrieval_improved", False))
            ),
        )

    def matched_target_refs(self) -> tuple[str, ...]:
        assessment_refs = self.evidence_assessment_obj().matched_target_ref_list()
        if assessment_refs:
            return tuple(str(item) for item in assessment_refs if item)
        summary = self._normalized_summary()
        return tuple(str(item) for item in summary.get("matched_target_refs", ()) if item)

    def target_count(self) -> int:
        assessment = self.evidence_assessment_obj()
        if assessment.has_target_coverage_state():
            return int(assessment.summary_view().target_count)
        summary = self._normalized_summary()
        return int(summary.get("target_count", len(self.targets)) or 0)

    def matched_target_count(self) -> int:
        assessment = self.evidence_assessment_obj()
        if assessment.has_target_coverage_state():
            return int(assessment.summary_view().matched_target_count)
        summary = self._normalized_summary()
        return int(summary.get("matched_target_count", 0) or 0)

    def status_summary(self) -> str:
        summary = self._normalized_summary()
        return str(summary.get("status_summary", self.status))

    def unsupported_target_refs(self) -> tuple[str, ...]:
        assessment_refs = self.evidence_assessment_obj().unsupported_target_ref_list()
        if assessment_refs:
            return tuple(str(item) for item in assessment_refs if item)
        summary = self._normalized_summary()
        return tuple(str(item) for item in summary.get("unsupported_target_refs", ()) if item)

    def needs_more_evidence_targets(self) -> tuple[str, ...]:
        assessment_refs = self.evidence_assessment_obj().needs_more_evidence_target_list()
        if assessment_refs:
            return tuple(str(item) for item in assessment_refs if item)
        summary = self._normalized_summary()
        return tuple(str(item) for item in summary.get("needs_more_evidence_targets", ()) if item)

    def follow_up_retrieval_attempted(self) -> bool:
        assessment = self.evidence_assessment_obj()
        if assessment.follow_up_attempted() or assessment.follow_up_retrieval:
            return assessment.follow_up_attempted()
        summary = self._normalized_summary()
        return bool(summary.get("follow_up_retrieval_attempted", False))

    def follow_up_retrieval_improved(self) -> bool:
        assessment = self.evidence_assessment_obj()
        if assessment.follow_up_attempted() or assessment.follow_up_retrieval:
            return assessment.follow_up_improved()
        summary = self._normalized_summary()
        return bool(summary.get("follow_up_retrieval_improved", False))

    def follow_up_retrieval_sources(self) -> tuple[str, ...]:
        assessment_sources = self.evidence_assessment_obj().follow_up_retrieval_source_refs()
        if assessment_sources:
            return assessment_sources
        summary = self._normalized_summary()
        return tuple(str(item) for item in summary.get("follow_up_retrieval_sources", ()) if item)

    def follow_up_retrieval_retrieved_evidence_count(self) -> int:
        assessment_count = self.evidence_assessment_obj().follow_up_retrieval_retrieved_evidence_count()
        if assessment_count:
            return int(assessment_count)
        summary = self._normalized_summary()
        return int(summary.get("follow_up_retrieval_retrieved_evidence_count", 0) or 0)

    @classmethod
    def from_dict(cls, payload: dict[str, Any] | None) -> "ReviewBundle":
        data = dict(payload or {})
        review_mode = str(data.get("review_mode", "not_applicable"))
        review_confidence = str(data.get("review_confidence", "not_applicable"))
        review_scope = str(data.get("review_scope", "not_applicable"))
        status = str(data.get("status", "not_applicable"))
        summary = dict(data.get("review_summary", {}))
        evidence_assessment_payload = data.get("evidence_assessment", {})
        if isinstance(evidence_assessment_payload, EvidenceAssessmentResult):
            evidence_assessment = evidence_assessment_payload
        else:
            evidence_assessment = EvidenceAssessmentResult.from_dict(dict(evidence_assessment_payload or {}))
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
            evidence_assessment=evidence_assessment,
            review_findings=tuple(dict(item) for item in data.get("review_findings", ()) or ()),
            review_summary=summary,
        )


@dataclass(frozen=True)
class ChallengeResult:
    status: str
    targets: tuple[dict[str, Any], ...] = ()
    evidence_assessment: EvidenceAssessmentResult | dict[str, Any] = field(default_factory=dict)
    review_findings: tuple[dict[str, Any], ...] = ()
    answer_constraints: dict[str, Any] = field(default_factory=dict)
    review_summary: dict[str, Any] = field(default_factory=dict)

    def evidence_assessment_obj(self) -> EvidenceAssessmentResult:
        if isinstance(self.evidence_assessment, EvidenceAssessmentResult):
            return self.evidence_assessment
        return EvidenceAssessmentResult.from_dict(dict(self.evidence_assessment or {}))

    @classmethod
    def from_review_evaluation(
        cls,
        *,
        targets: tuple[dict[str, Any], ...] = (),
        evidence_assessment: EvidenceAssessmentResult | dict[str, Any] | None = None,
        evaluation: ReviewEvaluationResult | dict[str, Any] | None = None,
        review_summary: dict[str, Any] | None = None,
    ) -> "ChallengeResult":
        assessment = (
            evidence_assessment
            if isinstance(evidence_assessment, EvidenceAssessmentResult)
            else EvidenceAssessmentResult.from_dict(dict(evidence_assessment or {}))
        )
        evaluation_result = (
            evaluation
            if isinstance(evaluation, ReviewEvaluationResult)
            else ReviewEvaluationResult.from_dict(dict(evaluation or {}))
        )
        return cls(
            status=evaluation_result.status,
            targets=targets,
            evidence_assessment=assessment,
            review_findings=evaluation_result.review_findings,
            answer_constraints=evaluation_result.answer_constraints,
            review_summary=dict(review_summary or {}),
        )

    def to_dict(self) -> dict[str, Any]:
        payload = self.review_bundle_obj().to_dict()
        payload["answer_constraints"] = dict(self.answer_constraints)
        return payload

    def review_bundle_obj(self) -> ReviewBundle:
        return self.to_review_bundle()

    def to_review_bundle(self) -> ReviewBundle:
        return ReviewBundle.from_review_evaluation(
            targets=self.targets,
            evidence_assessment=self.evidence_assessment_obj(),
            evaluation=ReviewEvaluationResult(
                status=self.status,
                review_findings=self.review_findings,
                answer_constraints=self.answer_constraints,
            ),
            review_summary=self.review_summary,
        )

    def review_summary_view(self) -> ReviewBundleSummaryView:
        return self.review_bundle_obj().summary_view()

    def matched_target_refs(self) -> tuple[str, ...]:
        return self.review_bundle_obj().matched_target_refs()

    def needs_more_evidence_targets(self) -> tuple[str, ...]:
        return self.review_bundle_obj().needs_more_evidence_targets()

    def follow_up_retrieval_attempted(self) -> bool:
        return self.review_bundle_obj().follow_up_retrieval_attempted()


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
    key_events: tuple[str, ...] = ()
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
            "key_events": list(self.key_events),
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
        return self.context_bundle_obj().summary_view()

    def plan_summary_view(self) -> PlanBundleSummaryView:
        return self.plan_bundle_obj().summary_view()

    def review_summary_view(self) -> ReviewBundleSummaryView:
        return self.review_bundle_obj().summary_view()

    def evidence_summary_view(self) -> EvidenceBundleSummaryView:
        if self.evidence_bundle is None:
            return EvidenceBundleSummaryView()
        return self.evidence_bundle.summary_view()
