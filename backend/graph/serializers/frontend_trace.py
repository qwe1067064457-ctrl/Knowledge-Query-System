"""Serialize graph decision objects into stable frontend trace payloads."""

from __future__ import annotations

from typing import Any


def _to_dict(value: Any) -> dict[str, Any]:
    """Reuse object-level contracts and fail loudly when the contract is missing."""
    if value is None or not hasattr(value, "to_dict"):
        raise TypeError("frontend trace serializer expects an object with to_dict()")
    payload = value.to_dict()
    if not isinstance(payload, dict):
        raise TypeError("frontend trace serializer expects to_dict() to return a dict")
    return payload


def serialize_intent_analysis(intent_analysis: Any) -> dict[str, Any]:
    """Expose the intent-analysis structure expected by the frontend."""
    return {
        "type": "intent_analysis",
        "input": _to_dict(getattr(intent_analysis, "input", None)),
        "evidence": _to_dict(getattr(intent_analysis, "evidence", None)),
        "resolved": _to_dict(getattr(intent_analysis, "resolved", None)),
        "control": _to_dict(getattr(intent_analysis, "control", None)),
    }


def serialize_workflow_plan(workflow_plan: Any) -> dict[str, Any]:
    """Wrap the existing workflow plan contract without adding runtime semantics."""
    return {
        "type": "workflow_plan",
        "plan": _to_dict(workflow_plan),
    }


def serialize_execution_payload(execution_payload: Any, *, stage: str) -> dict[str, Any]:
    """Expose route-level execution payload readiness for frontend trace rendering."""
    return {
        "type": "execution_update",
        "stage": stage,
        "payload": _to_dict(execution_payload),
    }
