from __future__ import annotations

from context.models import SessionDialogueState
from workflow.powers.context_binding_power import ContextBindingPower
from workflow.types import ContextBindingResult


def test_explicit_pattern_with_focus_object_uses_rule_binding() -> None:
    power = ContextBindingPower()
    candidates = [
        {"object_id": "question_1", "object_type": "question_object", "content": "旧问题", "source_power": "workflow"},
        {"object_id": "question_2", "object_type": "question_object", "content": "最新问题", "source_power": "workflow"},
    ]

    result = power.bind(
        "你刚才说的这个依据是什么",
        candidates,
        dialogue_state=SessionDialogueState(
            focus_question_object_id="question_2",
            focus_question_object_text="最新问题",
            resolution_confidence="high",
        ),
    )

    assert result.binding_ambiguous is False
    assert result.binding_confidence == "medium"
    assert result.bound_targets[0]["object_id"] == "question_2"
    assert result.matched_by == "focus_object_continuity"
    assert result.clarification_hint is None
    assert result.binding_summary


def test_explicit_followup_can_use_llm_resolution_and_rewrite() -> None:
    power = ContextBindingPower()
    candidates = [
        {"object_id": "question_1", "object_type": "question_object", "content": "MacBook Pro M3 重量多少？", "source_power": "workflow"},
        {"object_id": "question_2", "object_type": "question_object", "content": "Dell XPS 14 重量多少？", "source_power": "workflow"},
    ]

    def fake_llm_call(prompt: str) -> str:
        if "上一轮状态" in prompt:
            return '{"focus_question_object_id":"question_2","focus_question_object_text":"Dell XPS 14 重量多少？","focus_predicate":"重量","recent_question_objects":[{"object_id":"question_1","content":"MacBook Pro M3 重量多少？"},{"object_id":"question_2","content":"Dell XPS 14 重量多少？"}],"recent_evidence_topics":[],"resolution_confidence":"medium","last_update_reason":"llm_state_update"}'
        return '{"resolved_target_ids":["question_2"],"rewritten_query":"Dell XPS 14 重量多少？","confidence":"high","needs_clarification":false}'

    result = power.bind(
        "那它的重量呢？",
        candidates,
        recent_messages=[
            {"role": "user", "content": "MacBook Pro M3 重量多少？"},
            {"role": "assistant", "content": "1.6kg"},
            {"role": "user", "content": "那 Dell XPS 14 呢？"},
        ],
        llm_call=fake_llm_call,
        rewrite_query=True,
    )

    assert result.binding_ambiguous is False
    assert result.binding_confidence == "high"
    assert result.matched_by == "llm_resolution"
    assert result.bound_targets[0]["object_id"] == "question_2"
    assert result.rewritten_query == "Dell XPS 14 重量多少？"
    assert result.state_snapshot["focus_question_object_id"] == "question_2"


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
        {"object_id": "question_1", "object_type": "question_object", "content": "最新问题", "source_power": "workflow"},
    ]

    result = power.bind("你刚才说的这个依据是什么", candidates)
    payload = result.to_dict()

    assert isinstance(result, ContextBindingResult)
    assert payload["bound_targets"][0]["object_id"] == "question_1"
    assert payload["matched_by"] in {"single_candidate", "explicit_single_candidate", "explicit_pattern"}
    assert "state_snapshot" in payload
