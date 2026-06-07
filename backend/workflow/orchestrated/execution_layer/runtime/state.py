from __future__ import annotations

import operator
from typing import Annotated, Any
from typing_extensions import TypedDict


def merge_dicts(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    merged = dict(left or {})
    merged.update(dict(right or {}))
    return merged


def prefer_non_null(left: Any, right: Any) -> Any:
    return left if left is not None else right


class ExecutionRuntimeState(TypedDict):
    execution_graph: Any
    unit_results: Annotated[list[Any], operator.add]
    state_by_unit: Annotated[dict[str, str], merge_dicts]
    evidence_bundles: Annotated[list[Any], operator.add]
    evidence_candidates: Annotated[list[dict[str, Any]], operator.add]
    key_events: Annotated[list[str], operator.add]
    preferred_binding_result: Annotated[Any, prefer_non_null]
