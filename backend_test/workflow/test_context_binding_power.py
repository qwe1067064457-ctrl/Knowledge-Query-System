from __future__ import annotations

from workflow.powers.context_binding_power import ContextBindingPower


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
    assert result.notes == ("topic_continuity",)


def test_empty_candidates_falls_back_to_ambiguity() -> None:
    power = ContextBindingPower()

    result = power.bind("这个是什么意思", [])

    assert result.binding_ambiguous is True
    assert result.binding_confidence == "low"
