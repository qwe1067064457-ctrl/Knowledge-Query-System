from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from workflow.types import ContextBindingResult


BoundQueryExpectedMode = Literal["auto_bind", "clarify"]


@dataclass(frozen=True)
class BoundQueryEvalCase:
    case_id: str
    query: str
    expected_mode: BoundQueryExpectedMode
    expected_target_ids: tuple[str, ...] = ()
    expected_rewritten_query: str | None = None


@dataclass(frozen=True)
class BoundQueryEvalOutcome:
    case_id: str
    expected_mode: BoundQueryExpectedMode
    actual_mode: BoundQueryExpectedMode
    expected_target_ids: tuple[str, ...]
    actual_target_ids: tuple[str, ...]
    expected_rewritten_query: str | None
    actual_rewritten_query: str | None
    is_correct: bool
    is_misbind: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "expected_mode": self.expected_mode,
            "actual_mode": self.actual_mode,
            "expected_target_ids": list(self.expected_target_ids),
            "actual_target_ids": list(self.actual_target_ids),
            "expected_rewritten_query": self.expected_rewritten_query,
            "actual_rewritten_query": self.actual_rewritten_query,
            "is_correct": self.is_correct,
            "is_misbind": self.is_misbind,
        }


def evaluate_bound_query_case(
    case: BoundQueryEvalCase,
    result: ContextBindingResult,
) -> BoundQueryEvalOutcome:
    actual_mode: BoundQueryExpectedMode = "clarify" if result.binding_ambiguous else "auto_bind"
    actual_target_ids = tuple(
        str(item.get("object_id") or "")
        for item in result.bound_targets
        if str(item.get("object_id") or "").strip()
    )
    actual_rewritten_query = str(result.rewritten_query).strip() if result.rewritten_query else None

    is_mode_correct = actual_mode == case.expected_mode
    is_target_correct = actual_target_ids == case.expected_target_ids
    is_rewrite_correct = (
        case.expected_rewritten_query is None
        or actual_rewritten_query == case.expected_rewritten_query
    )
    is_correct = is_mode_correct and is_target_correct and is_rewrite_correct
    is_misbind = (
        case.expected_mode == "auto_bind"
        and actual_mode == "auto_bind"
        and actual_target_ids != case.expected_target_ids
    )
    return BoundQueryEvalOutcome(
        case_id=case.case_id,
        expected_mode=case.expected_mode,
        actual_mode=actual_mode,
        expected_target_ids=case.expected_target_ids,
        actual_target_ids=actual_target_ids,
        expected_rewritten_query=case.expected_rewritten_query,
        actual_rewritten_query=actual_rewritten_query,
        is_correct=is_correct,
        is_misbind=is_misbind,
    )


def summarize_bound_query_outcomes(
    outcomes: list[BoundQueryEvalOutcome],
) -> dict[str, Any]:
    total = len(outcomes)
    actual_auto_binds = [item for item in outcomes if item.actual_mode == "auto_bind"]
    clarifications = [item for item in outcomes if item.actual_mode == "clarify"]
    misbinds = [item for item in outcomes if item.is_misbind]
    correct_auto_binds = [item for item in actual_auto_binds if item.is_correct]
    return {
        "total_cases": total,
        "auto_bind_count": len(actual_auto_binds),
        "clarification_count": len(clarifications),
        "misbind_count": len(misbinds),
        "auto_bind_precision": (
            len(correct_auto_binds) / len(actual_auto_binds) if actual_auto_binds else 0.0
        ),
        "clarification_rate": (len(clarifications) / total) if total else 0.0,
        "misbind_rate": (len(misbinds) / total) if total else 0.0,
        "correct_case_rate": (
            len([item for item in outcomes if item.is_correct]) / total if total else 0.0
        ),
        "outcomes": [item.to_dict() for item in outcomes],
    }
