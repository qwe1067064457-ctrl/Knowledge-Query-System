"""
Project workflow execution payloads into context-registry entries and
define the boundary between workflow-owned summary metadata and registry
convenience metadata.
"""
from __future__ import annotations

import time
from typing import Any

from context.registry.registry_types import ContextRegistryEntry, RegistryObjectType


_REGISTRY_OBJECT_TYPES: set[RegistryObjectType] = {
    "evidence_ref",
    "question_object",
}

_QUESTION_CONVENIENCE_KEYS = {"route", "handling_mode", "unit_id", "origin"}
_EVIDENCE_CONVENIENCE_KEYS = {"source_type", "channel", "query_unit_ids"}


def build_registry_metadata_payload(
    *,
    owner_summary: dict[str, Any],
    convenience_fields: dict[str, Any] | None = None,
) -> dict[str, Any]:
    convenience = dict(convenience_fields or {})
    payload = {**convenience, **owner_summary}
    payload["workflow_summary"] = owner_summary
    payload["registry_convenience"] = convenience
    return payload


def _whitelist_convenience_fields(
    fields: dict[str, Any] | None,
    *,
    allowed_keys: set[str],
) -> dict[str, Any]:
    payload = dict(fields or {})
    return {
        key: payload[key]
        for key in allowed_keys
        if payload.get(key) is not None
    }


def build_execution_summary_metadata(payload) -> dict[str, Any]:
    context_summary = payload.context_summary_view()
    plan_summary_view = payload.plan_summary_view()
    review_summary_view = payload.review_summary_view()
    evidence_summary_view = payload.evidence_summary_view()
    plan_bundle = payload.plan_bundle_obj()
    review_bundle = payload.review_bundle_obj()

    evidence_summary = {}
    if getattr(payload, "evidence_bundle", None) is not None:
        evidence_summary = {
            "retrieval_quality_status": evidence_summary_view.retrieval_quality_status,
            "query_unit_count": evidence_summary_view.query_unit_count,
            "merged_evidence_count": evidence_summary_view.merged_evidence_count,
            "source_ref_count": evidence_summary_view.source_ref_count,
            "repairable_units": evidence_summary_view.repairable_units,
            "repaired_units": evidence_summary_view.repaired_units,
            "missing_evidence": evidence_summary_view.missing_evidence,
            "coverage_query_units": evidence_summary_view.coverage_query_units,
            "coverage_sources": evidence_summary_view.coverage_sources,
        }
    plan_summary = {
        "planning_mode": plan_summary_view.planning_mode,
        "step_count": plan_summary_view.step_count,
        "checkpoint_count": plan_summary_view.checkpoint_count,
        "comparison_unit_count": plan_summary_view.comparison_unit_count,
        "bound_target_ref_count": plan_summary_view.bound_target_ref_count,
        "refined": plan_summary_view.refined,
        "fallback_used": plan_summary_view.fallback_used,
        "fallback_reason": list(plan_bundle.fallback_reason),
    }
    review_summary = {
        "target_count": review_summary_view.target_count,
        "matched_target_count": review_summary_view.matched_target_count,
        "matched_target_refs": list(review_bundle.matched_target_refs()),
        "unsupported_target_refs": list(review_bundle.unsupported_target_refs()),
        "needs_more_evidence_targets": list(review_bundle.needs_more_evidence_targets()),
        "status_summary": review_summary_view.status_summary,
        "review_mode": review_summary_view.review_mode,
        "review_confidence": review_summary_view.review_confidence,
        "review_scope": review_summary_view.review_scope,
        "follow_up_retrieval_attempted": review_summary_view.follow_up_retrieval_attempted,
        "follow_up_retrieval_improved": review_summary_view.follow_up_retrieval_improved,
        "follow_up_retrieval_sources": list(review_bundle.follow_up_retrieval_sources()),
        "follow_up_retrieval_retrieved_evidence_count": review_bundle.follow_up_retrieval_retrieved_evidence_count(),
    }

    return {
        "knowledge_scope_status": str(getattr(payload, "knowledge_scope_status", "resolved")),
        "binding_summary": context_summary.binding_summary,
        "context_summary": {
            "candidate_count": context_summary.candidate_count,
            "query_unit_count": context_summary.query_unit_count,
            "memory_anchor_count": context_summary.memory_anchor_count,
            "hydrated_memory_entry_count": context_summary.hydrated_memory_entry_count,
            "memory_hydrated": context_summary.memory_hydrated,
            "binding_matched_by": context_summary.binding_matched_by,
            "binding_fallback_type": context_summary.binding_fallback_type,
            "binding_reason": context_summary.binding_reason,
        },
        "plan_summary": plan_summary,
        "review_summary": review_summary,
        "evidence_summary": evidence_summary,
    }


def build_registry_entries_from_execution_payload(
    *,
    payload,
    session_id: str,
    tenant_id: str,
    group_id: str,
    message: str,
) -> list[ContextRegistryEntry]:
    turn_id = f"turn_{int(time.time() * 1000)}"
    summary_metadata = build_execution_summary_metadata(payload)
    plan_bundle = payload.plan_bundle_obj()

    entries: list[ContextRegistryEntry] = [
        ContextRegistryEntry(
            object_id=f"{turn_id}:question",
            object_type="question_object",
            tenant_id=tenant_id,
            group_id=group_id,
            session_id=session_id,
            source_turn_id=turn_id,
            content=message,
            refs=(),
            salience_score=1.0,
            source_power="workflow",
            metadata=build_registry_metadata_payload(
                owner_summary=summary_metadata,
                convenience_fields=_whitelist_convenience_fields(
                    {
                        "route": payload.route,
                        "handling_mode": payload.handling_mode,
                    },
                    allowed_keys=_QUESTION_CONVENIENCE_KEYS,
                ),
            ),
        )
    ]

    if payload.evidence_bundle:
        for index, item in enumerate(payload.evidence_bundle.merged_evidence_items, start=1):
            entries.append(
                ContextRegistryEntry(
                    object_id=f"{turn_id}:evidence:{index}",
                    object_type="evidence_ref",
                    tenant_id=tenant_id,
                    group_id=group_id,
                    session_id=session_id,
                    source_turn_id=turn_id,
                    content=item.snippet,
                    refs=(item.source_path, item.locator, *item.query_unit_ids),
                    salience_score=float(item.score or 0.0),
                    source_power="retrieval_power",
                    metadata=build_registry_metadata_payload(
                        owner_summary=summary_metadata,
                        convenience_fields=_whitelist_convenience_fields(
                            {
                                "source_type": item.source_type,
                                "channel": item.channel,
                                "query_unit_ids": list(item.query_unit_ids),
                            },
                            allowed_keys=_EVIDENCE_CONVENIENCE_KEYS,
                        ),
                    ),
                )
            )

    for index, unit in enumerate(plan_bundle.query_unit_dicts(), start=1):
        if not _is_registry_worthy_query_unit(unit):
            continue
        entries.append(
            ContextRegistryEntry(
                object_id=f"{turn_id}:query-unit:{index}",
                object_type="question_object",
                tenant_id=tenant_id,
                group_id=group_id,
                session_id=session_id,
                source_turn_id=turn_id,
                content=str(unit.get("text", "")),
                refs=(),
                salience_score=0.75,
                source_power="decomposition_power",
                metadata=build_registry_metadata_payload(
                    owner_summary=summary_metadata,
                    convenience_fields=_whitelist_convenience_fields(
                        {
                            "unit_id": str(unit.get("unit_id", "")),
                            "origin": str(unit.get("origin", "")),
                        },
                        allowed_keys=_QUESTION_CONVENIENCE_KEYS,
                    ),
                ),
            )
        )

    return entries[:10]


def normalize_registry_object_type(value: Any) -> RegistryObjectType:
    object_type = str(value or "question_object")
    if object_type not in _REGISTRY_OBJECT_TYPES:
        return "question_object"
    return object_type  # type: ignore[return-value]


def _is_registry_worthy_query_unit(unit: dict[str, Any]) -> bool:
    unit_id = str(unit.get("unit_id", "")).strip()
    text = str(unit.get("text", "")).strip()
    origin = str(unit.get("origin", "")).strip()
    return bool(unit_id and text and origin)
