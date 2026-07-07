from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal


PlannerUnitCapability = Literal["qa_like", "compare", "verify", "synthesis"]

PLANNER_UNIT_CAPABILITIES = {"qa_like", "compare", "verify", "synthesis"}
MAX_UNIT_GROUPS = 5
MAX_TOTAL_UNITS = 10
_BARE_REFERENCE_MARKERS = ("它", "这个", "那个", "刚才", "上述", "前面")


@dataclass(frozen=True)
class GroupedUnit:
    unit_id: str
    capability: PlannerUnitCapability
    query: str

    def to_dict(self) -> dict[str, str]:
        return {"id": self.unit_id, "type": self.capability, "query": self.query}


@dataclass(frozen=True)
class GroupedUnitPlan:
    unit_groups: tuple[tuple[GroupedUnit, ...], ...]

    def to_dict(self) -> dict[str, list[list[dict[str, str]]]]:
        return {
            "unit_groups": [
                [unit.to_dict() for unit in group]
                for group in self.unit_groups
            ]
        }

    def unit_group_dicts(self) -> tuple[tuple[dict[str, str], ...], ...]:
        return tuple(tuple(unit.to_dict() for unit in group) for group in self.unit_groups)

    def total_units(self) -> int:
        return sum(len(group) for group in self.unit_groups)


def grouped_plan_from_payload(payload: dict[str, Any], *, require_synthesis_for_complex: bool = True) -> GroupedUnitPlan:
    groups_payload = payload.get("unit_groups")
    if not isinstance(groups_payload, list) or not groups_payload:
        raise ValueError("grouped_plan_missing_unit_groups")
    if len(groups_payload) > MAX_UNIT_GROUPS:
        raise ValueError("grouped_plan_too_many_groups")

    unit_groups: list[tuple[GroupedUnit, ...]] = []
    seen_ids: set[str] = set()
    for group_index, group_payload in enumerate(groups_payload, start=1):
        if not isinstance(group_payload, list) or not group_payload:
            raise ValueError("grouped_plan_empty_group")
        group: list[GroupedUnit] = []
        for unit_index, unit_payload in enumerate(group_payload, start=1):
            if not isinstance(unit_payload, dict):
                raise ValueError("grouped_plan_invalid_unit")
            unit_id = str(unit_payload.get("id") or unit_payload.get("unit_id") or "").strip()
            capability = str(unit_payload.get("type") or unit_payload.get("capability") or "").strip()
            query = str(unit_payload.get("query") or unit_payload.get("goal") or "").strip()
            if not unit_id:
                raise ValueError("grouped_plan_missing_unit_id")
            if unit_id in seen_ids:
                raise ValueError("grouped_plan_duplicate_unit_id")
            if capability not in PLANNER_UNIT_CAPABILITIES:
                raise ValueError("grouped_plan_invalid_capability")
            if not query:
                raise ValueError("grouped_plan_missing_query")
            if _has_bare_reference(query):
                raise ValueError("grouped_plan_bare_reference_query")
            seen_ids.add(unit_id)
            group.append(GroupedUnit(unit_id=unit_id, capability=capability, query=query))  # type: ignore[arg-type]
        unit_groups.append(tuple(group))

    plan = GroupedUnitPlan(unit_groups=tuple(unit_groups))
    if plan.total_units() > MAX_TOTAL_UNITS:
        raise ValueError("grouped_plan_too_many_units")
    if require_synthesis_for_complex and _is_complex_plan(plan):
        last_group = plan.unit_groups[-1]
        if len(last_group) != 1 or last_group[0].capability != "synthesis":
            raise ValueError("grouped_plan_missing_final_synthesis")
    return plan


def _is_complex_plan(plan: GroupedUnitPlan) -> bool:
    return len(plan.unit_groups) > 1 or plan.total_units() > 1


def _has_bare_reference(query: str) -> bool:
    return any(marker in query for marker in _BARE_REFERENCE_MARKERS)
