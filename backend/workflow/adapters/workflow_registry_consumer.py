"""
Define workflow-side registry consumption rules.
"""
from __future__ import annotations

from typing import Any

from workflow.types import EvidenceRefCandidate

_BINDING_OBJECT_TYPES = {"claim", "question_object", "case_or_scenario"}
_CHALLENGE_TARGET_TYPES = {"claim", "question_object"}
_PLANNING_OBJECT_TYPES = {"comparison_target", "question_object"}


def normalize_registry_entries(entries: list[dict[str, Any]] | tuple[dict[str, Any], ...] | tuple[Any, ...]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for entry in entries:
        if isinstance(entry, dict):
            normalized.append(dict(entry))
        elif hasattr(entry, "to_dict"):
            normalized.append(entry.to_dict())
    return normalized


def binding_candidates(entries: list[dict[str, Any]] | tuple[Any, ...]) -> list[dict[str, Any]]:
    normalized = normalize_registry_entries(entries)
    preferred = [
        candidate
        for candidate in normalized
        if candidate.get("object_type") in _BINDING_OBJECT_TYPES
    ]
    if preferred:
        return preferred
    return [
        candidate
        for candidate in normalized
        if candidate.get("object_type") == "comparison_target"
    ]


def challenge_target_candidates(entries: list[dict[str, Any]] | tuple[Any, ...]) -> list[dict[str, Any]]:
    return [
        candidate
        for candidate in normalize_registry_entries(entries)
        if candidate.get("object_type") in _CHALLENGE_TARGET_TYPES
    ]


def planning_candidates(entries: list[dict[str, Any]] | tuple[Any, ...]) -> list[dict[str, Any]]:
    return [
        candidate
        for candidate in normalize_registry_entries(entries)
        if candidate.get("object_type") in _PLANNING_OBJECT_TYPES
    ]


def evidence_candidates(entries: list[dict[str, Any]] | tuple[Any, ...]) -> list[EvidenceRefCandidate]:
    candidates: list[EvidenceRefCandidate] = []
    for candidate in normalize_registry_entries(entries):
        if candidate.get("object_type") != "evidence_ref":
            continue
        convenience = dict(candidate.get("metadata", {}).get("registry_convenience", {}))
        payload = dict(candidate)
        if payload.get("source_type") is None and convenience.get("source_type") is not None:
            payload["source_type"] = convenience.get("source_type")
        if payload.get("channel") is None and convenience.get("channel") is not None:
            payload["channel"] = convenience.get("channel")
        candidates.append(EvidenceRefCandidate.from_dict(payload))
    return candidates
