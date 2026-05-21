from __future__ import annotations

from workflow.powers.context_binding_power import ContextBindingPower
from workflow.types import ContextBindingResult


def test_explicit_pattern_binds_latest_candidate() -> None:
    power = ContextBindingPower()
    candidates = [
        {"object_id": "claim_1", "object_type": "claim", "content": "旧结论", "source_power": "challenge_power"},
        {"object_id": "claim_2", "object_type": "claim", "content": "最新结论", "source_power": "challenge_power"},
    ]

    result = power.bind("你刚才说的这个依据是什么", candidates)

    assert result.binding_ambiguous is False
    assert result.binding_confidence == "high"
    assert result.bound_targets[0]["object_id"] == "claim_2"
    assert result.matched_by == "explicit_pattern"
    assert result.clarification_hint is None
    assert result.binding_summary


def test_short_followup_uses_topic_continuity() -> None:
    power = ContextBindingPower()
    candidates = [
        {"object_id": "compare_1", "object_type": "comparison_target", "content": "A vs B", "source_power": "planning_power"},
        {"object_id": "compare_2", "object_type": "comparison_target", "content": "C vs D", "source_power": "planning_power"},
    ]

    result = power.bind(
        "所以明确怎么match了吗",
        candidates,
        recent_power="planning_power",
        recent_object_type="comparison_target",
    )

    assert result.binding_ambiguous is False
    assert result.binding_confidence == "medium"
    assert result.matched_by == "topic_continuity"
    assert result.notes[0].startswith("topic_continuity")
    assert result.binding_summary


def test_empty_candidates_falls_back_to_ambiguity() -> None:
    power = ContextBindingPower()

    result = power.bind("这个是什么意思", [])

    assert result.binding_ambiguous is True
    assert result.binding_confidence == "low"
    assert result.matched_by == "ambiguity_fallback"
    assert result.clarification_hint
    assert result.binding_summary


def test_ambiguous_binding_returns_candidate_based_hint() -> None:
    power = ContextBindingPower()
    candidates = [
        {"object_id": "claim_1", "object_type": "claim", "content": "第一个结论", "source_power": "challenge_power"},
        {"object_id": "claim_2", "object_type": "claim", "content": "第二个结论", "source_power": "challenge_power"},
    ]

    result = power.bind("请解释这里的含义", candidates)

    assert result.binding_ambiguous is True
    assert result.clarification_hint
    assert "第一个结论" in result.clarification_hint or "第二个结论" in result.clarification_hint
    assert result.binding_summary


def test_binding_power_returns_public_typed_binding_result() -> None:
    power = ContextBindingPower()
    candidates = [
        {"object_id": "claim_1", "object_type": "claim", "content": "最新结论", "source_power": "challenge_power"},
    ]

    result = power.bind("你刚才说的这个依据是什么", candidates)
    payload = result.to_dict()

    assert isinstance(result, ContextBindingResult)
    assert payload["bound_targets"][0]["object_id"] == "claim_1"
    assert payload["matched_by"] == "explicit_pattern"
