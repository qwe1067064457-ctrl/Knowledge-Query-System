from __future__ import annotations

from dataclasses import replace
from typing import Any, Iterable, Protocol

from intent.pipeline.adjudication_prompts import build_adjudication_prompt
from intent.schema.evidence_types import AdjudicationResult, EvidenceQualityReport, TypedEvidence
from intent.schema.intent_types import (
    CandidateIntent,
    ContextSignals,
    IntentEvidence,
    IntentInput,
    SignalBuckets,
    TaskCandidate,
)


class IntentAdjudicator(Protocol):
    def adjudicate(
        self,
        *,
        intent_input: IntentInput,
        typed_evidence: tuple[TypedEvidence, ...],
        quality_report: EvidenceQualityReport,
        history: Iterable[dict[str, Any]],
    ) -> AdjudicationResult | None: ...


def run_adjudication(
    *,
    adjudicator: IntentAdjudicator,
    intent_input: IntentInput,
    evidence: IntentEvidence,
    history: Iterable[dict[str, Any]],
) -> AdjudicationResult | None:
    """Call an adjudicator only after the quality gate asks for LLM help."""

    if evidence.quality_report is None:
        return None
    build_adjudication_prompt(
        intent_input=intent_input,
        typed_evidence=evidence.typed_evidence,
        quality_report=evidence.quality_report,
    )
    return adjudicator.adjudicate(
        intent_input=intent_input,
        typed_evidence=evidence.typed_evidence,
        quality_report=evidence.quality_report,
        history=history,
    )


def apply_adjudication_result(
    evidence: IntentEvidence,
    result: AdjudicationResult,
) -> IntentEvidence:
    """Merge adjudicated evidence into legacy fields consumed by resolver."""

    trusted = (*result.accepted_evidence, *result.corrected_evidence)
    signal_buckets = _merge_signal_buckets(evidence.signal_buckets, trusted)
    unsupported_signals = dict(evidence.unsupported_signals)
    for item in trusted:
        if item.signal in {"unsupported", "out_of_scope"}:
            unsupported_signals["unknown_external_action"] = True

    return replace(
        evidence,
        signal_buckets=signal_buckets,
        unsupported_signals=unsupported_signals,
        context_signals=_merge_context_signals(evidence.context_signals, trusted),
        candidate_intents=_merge_candidate_intents(evidence.candidate_intents, trusted),
        task_candidates=_merge_task_candidates(evidence.task_candidates, trusted),
        adjudication_result=result,
    )


def _merge_candidate_intents(
    existing: tuple[CandidateIntent, ...],
    trusted: tuple[TypedEvidence, ...],
) -> tuple[CandidateIntent, ...]:
    merged = {item.intent: item for item in existing}
    for item in trusted:
        if item.signal != "main_intent" or item.value not in {"qa", "chat", "system", "unsupported"}:
            continue
        score = item.score if item.score is not None else 0.95
        current = merged.get(item.value)
        if current is None or score > current.score:
            merged[item.value] = CandidateIntent(intent=item.value, score=score)
    return tuple(merged.values())


def _merge_task_candidates(
    existing: tuple[TaskCandidate, ...],
    trusted: tuple[TypedEvidence, ...],
) -> tuple[TaskCandidate, ...]:
    merged = {(item.complexity, item.shape, item.topology): item for item in existing}
    for item in trusted:
        if item.signal != "task_candidate" or not isinstance(item.value, dict):
            continue
        candidate = _task_candidate_from_value(item.value, item.score)
        key = (candidate.complexity, candidate.shape, candidate.topology)
        current = merged.get(key)
        if current is None or candidate.score > current.score:
            merged[key] = candidate
    return tuple(merged.values())


def _merge_signal_buckets(
    buckets: SignalBuckets,
    trusted: tuple[TypedEvidence, ...],
) -> SignalBuckets:
    intent = list(buckets.intent)
    task = list(buckets.task)
    context = list(buckets.context)
    safety = list(buckets.safety)
    for item in trusted:
        signal = item.signal
        if signal == "main_intent" and isinstance(item.value, str):
            _append_unique(intent, item.value)
        elif signal in {"follow_up", "challenge", "soft_doubt", "ask_source", "ask_capability"}:
            _append_unique(intent, signal)
        elif signal in {"multi_question", "parallel_subtasks", "staged", "complex"}:
            _append_unique(task, signal)
        elif signal in {"history_reference", "needs_previous_answer", "previous_retrieval", "clarify_hint"}:
            _append_unique(context, signal)
        elif signal in {"unsupported", "out_of_scope"}:
            _append_unique(safety, "unsupported")
            _append_unique(safety, "out_of_scope")
    return SignalBuckets(intent=tuple(intent), task=tuple(task), context=tuple(context), safety=tuple(safety))


def _merge_context_signals(
    current: ContextSignals,
    trusted: tuple[TypedEvidence, ...],
) -> ContextSignals:
    signals = {item.signal for item in trusted if item.value}
    missing = list(current.missing_context_types)
    ambiguity = list(current.ambiguity_states)
    if "clarify_hint" in signals and "adjudicated_ambiguity" not in ambiguity:
        ambiguity.append("adjudicated_ambiguity")
    return ContextSignals(
        history_reference=current.history_reference or "history_reference" in signals,
        needs_previous_answer=current.needs_previous_answer or "needs_previous_answer" in signals,
        previous_retrieval=current.previous_retrieval or "previous_retrieval" in signals,
        clarify_hint=current.clarify_hint or "clarify_hint" in signals,
        ambiguity_states=tuple(ambiguity),
        missing_context_types=tuple(missing),
    )


def _task_candidate_from_value(value: dict[str, Any], score: float | None) -> TaskCandidate:
    return TaskCandidate(
        complexity=value.get("complexity", "simple"),
        shape=value.get("shape", "single_question"),
        score=score if score is not None else float(value.get("score", 0.9)),
        topology=value.get("topology", "single"),
    )


def _append_unique(items: list[str], value: str) -> None:
    if value and value not in items:
        items.append(value)
