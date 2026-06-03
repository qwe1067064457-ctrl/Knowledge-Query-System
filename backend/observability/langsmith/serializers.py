from __future__ import annotations

from collections import Counter
from typing import Any


def summarize_messages(messages: list[dict[str, Any]]) -> dict[str, Any]:
    roles = Counter(str(item.get("role") or "") for item in messages)
    system_prefixes: list[str] = []
    latest_user_query = ""
    for item in messages:
        role = str(item.get("role") or "")
        content = str(item.get("content") or "")
        if role == "system" and content.startswith("["):
            first_line = content.splitlines()[0].strip()
            if first_line and first_line not in system_prefixes:
                system_prefixes.append(first_line)
        if role == "user" and content:
            latest_user_query = content[:200]
    return {
        "message_count": len(messages),
        "role_distribution": dict(roles),
        "system_blocks": system_prefixes,
        "latest_user_query": latest_user_query,
    }


def summarize_execution_payload(payload) -> dict[str, Any]:
    evidence_summary = payload.evidence_summary_view()
    plan_summary = payload.plan_summary_view()
    context_summary = payload.context_summary_view()
    return {
        "route": payload.route,
        "action": payload.action,
        "status": payload.status,
        "enabled_powers": list(payload.enabled_powers),
        "context_summary": {
            "binding_summary": context_summary.binding_summary,
            "candidate_count": context_summary.candidate_count,
            "query_unit_count": context_summary.query_unit_count,
            "memory_anchor_count": context_summary.memory_anchor_count,
            "memory_hydrated": context_summary.memory_hydrated,
        },
        "plan_summary": {
            "planning_mode": plan_summary.planning_mode,
            "step_count": plan_summary.step_count,
            "checkpoint_count": plan_summary.checkpoint_count,
            "execution_unit_count": plan_summary.execution_unit_count,
            "dag": plan_summary.dag,
        },
        "evidence_summary": {
            "retrieval_quality_status": evidence_summary.retrieval_quality_status,
            "query_unit_count": evidence_summary.query_unit_count,
            "merged_evidence_count": evidence_summary.merged_evidence_count,
            "source_ref_count": evidence_summary.source_ref_count,
            "missing_evidence": evidence_summary.missing_evidence,
        },
        "key_events": list(payload.key_events),
    }


def summarize_evidence_bundle(bundle) -> dict[str, Any]:
    if bundle is None:
        return {
            "retrieval_quality_status": "not_applicable",
            "query_unit_count": 0,
            "merged_evidence_count": 0,
            "source_ref_count": 0,
            "missing_evidence": False,
        }
    summary = bundle.summary_view()
    return {
        "retrieval_quality_status": summary.retrieval_quality_status,
        "query_unit_count": summary.query_unit_count,
        "merged_evidence_count": summary.merged_evidence_count,
        "source_ref_count": summary.source_ref_count,
        "missing_evidence": summary.missing_evidence,
        "coverage_query_units": summary.coverage_query_units,
        "coverage_sources": summary.coverage_sources,
    }


def summarize_compaction_slice(
    *,
    slice_start_entry_id: str | None,
    slice_end_entry_id: str | None,
    slice_messages: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "slice_start_entry_id": slice_start_entry_id,
        "slice_end_entry_id": slice_end_entry_id,
        "slice_message_count": len(slice_messages),
        "slice_message_roles": [str(item.get("role") or "") for item in slice_messages],
    }
