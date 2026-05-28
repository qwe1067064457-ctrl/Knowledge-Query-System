from __future__ import annotations

from memory_system.session_working_memory.models import SessionWorkingMemory, WorkingMemoryEntry, WorkingMemoryHead
from workflow.powers.context_binding_power import ContextBindingPower
from workflow.types import ContextBindingResult


def _working_memory(*entries: WorkingMemoryEntry) -> SessionWorkingMemory:
    return SessionWorkingMemory(
        entries=list(entries),
        head=WorkingMemoryHead(active_entry_ids=[entry.entry_id for entry in entries]),
    )


def test_explicit_second_point_uses_relevant_set_rule_resolution() -> None:
    power = ContextBindingPower()
    memory = _working_memory(
        WorkingMemoryEntry(
            entry_id="wm_answer_1",
            entry_type="answer_unit",
            turn_id="turn_1",
            source_kind="answer",
            source_ref="turn_1:answer:1",
            content="第一点：先确认试用期的合同期限。",
            structured_payload={"unit_index": 1},
            confidence="high",
        ),
        WorkingMemoryEntry(
            entry_id="wm_answer_2",
            entry_type="answer_unit",
            turn_id="turn_1",
            source_kind="answer",
            source_ref="turn_1:answer:2",
            content="第二点：一年期劳动合同试用期上限为一个月。",
            structured_payload={"unit_index": 2},
            confidence="high",
        ),
    )

    result = power.bind(
        "第二点怎么落地？",
        [],
        working_memory=memory,
        rewrite_query=True,
    )

    assert result.binding_ambiguous is False
    assert result.matched_by == "ordinal_rule"
    assert result.relevant_set[0]["object_id"] == "wm_answer_2"
    assert result.resolved_target_ids == ("wm_answer_2",)
    assert result.bound_targets[0]["object_id"] == "wm_answer_2"
    assert result.binding_snapshot["query_style"] == "follow_up"


def test_followup_can_use_llm_resolution_after_relevant_set_filtering() -> None:
    power = ContextBindingPower()
    memory = _working_memory(
        WorkingMemoryEntry(
            entry_id="wm_answer_mac",
            entry_type="answer_unit",
            turn_id="turn_1",
            source_kind="answer",
            source_ref="turn_1:answer:1",
            content="MacBook Pro M3 重量约 1.6kg。",
            structured_payload={"unit_index": 1},
            confidence="high",
        ),
        WorkingMemoryEntry(
            entry_id="wm_answer_dell",
            entry_type="answer_unit",
            turn_id="turn_2",
            source_kind="answer",
            source_ref="turn_2:answer:1",
            content="Dell XPS 14 重量约 1.7kg。",
            structured_payload={"unit_index": 1},
            confidence="high",
        ),
    )

    def fake_llm_call(prompt: str) -> str:
        assert "候选相关对象" in prompt
        return '{"resolved_target_ids":["wm_answer_dell"],"rewritten_query":"Dell XPS 14 重量多少？","confidence":"high","needs_clarification":false,"fallback_type":null,"reason":null}'

    result = power.bind(
        "那它的重量呢？",
        [],
        working_memory=memory,
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
    assert result.resolved_target_ids == ("wm_answer_dell",)
    assert result.rewritten_query == "Dell XPS 14 重量多少？"
    assert result.binding_snapshot["relevant_set_size"] >= 1


def test_memory_anchor_can_enter_relevant_set_for_llm_resolution() -> None:
    power = ContextBindingPower()

    def fake_llm_call(prompt: str) -> str:
        assert "memory_anchor" in prompt
        return '{"resolved_target_ids":["session_older"],"rewritten_query":"那个案例的结论是什么","confidence":"medium","needs_clarification":false,"fallback_type":null,"reason":null}'

    result = power.bind(
        "那个案例的结论是什么？",
        [],
        memory_anchors=[
            {
                "source_session_id": "session_older",
                "summary": "之前讨论过一个竞业限制案例。",
                "confidence": "medium",
            }
        ],
        recent_messages=[{"role": "user", "content": "我们之前聊过一个竞业限制案例。"}],
        llm_call=fake_llm_call,
        rewrite_query=True,
    )

    assert result.binding_ambiguous is False
    assert result.resolved_target_ids == ("session_older",)
    assert result.relevant_set[0]["object_type"] == "memory_anchor"


def test_empty_relevant_set_for_followup_returns_clarification_fallback() -> None:
    power = ContextBindingPower()

    result = power.bind("这个是什么意思", [])

    assert result.binding_ambiguous is True
    assert result.needs_clarification is True
    assert result.fallback_type == "needs_clarification"
    assert result.reason == "no_relevant_targets"
    assert result.clarification_hint


def test_self_contained_query_without_targets_falls_back_to_raw_retrieval() -> None:
    power = ContextBindingPower()

    result = power.bind("一年期劳动合同试用期上限是多少？", [])

    assert result.binding_ambiguous is False
    assert result.fallback_type == "retrieve_on_raw_query"
    assert result.reason == "query_self_contained"
    assert result.binding_snapshot["query_style"] == "standalone"


def test_self_contained_comparison_query_is_not_misclassified_as_multi_target() -> None:
    power = ContextBindingPower()

    result = power.bind("working memory 和 memory anchor 的区别是什么", [])

    assert result.binding_snapshot["query_style"] == "standalone"
    assert result.fallback_type == "retrieve_on_raw_query"
    assert result.reason == "query_self_contained"


def test_true_multi_target_query_still_uses_multi_target_style() -> None:
    power = ContextBindingPower()
    memory = _working_memory(
        WorkingMemoryEntry(
            entry_id="wm_answer_1",
            entry_type="answer_unit",
            turn_id="turn_1",
            source_kind="answer",
            source_ref="turn_1:answer:1",
            content="第一点：先确认试用期的合同期限。",
            structured_payload={"unit_index": 1},
            confidence="high",
        ),
        WorkingMemoryEntry(
            entry_id="wm_answer_2",
            entry_type="answer_unit",
            turn_id="turn_1",
            source_kind="answer",
            source_ref="turn_1:answer:2",
            content="第二点：一年期劳动合同试用期上限为一个月。",
            structured_payload={"unit_index": 2},
            confidence="high",
        ),
    )

    result = power.bind("前两个分别怎么处理？", [], working_memory=memory, rewrite_query=True)

    assert result.binding_snapshot["query_style"] == "multi_target"
    assert result.resolved_target_ids == ("wm_answer_1", "wm_answer_2")
    assert result.matched_by == "ordinal_rule"


def test_summary_query_with_dou_is_not_forced_into_multi_target_style() -> None:
    power = ContextBindingPower()

    result = power.bind(
        "所以我们都需要一个 relevant set 吗？",
        [],
        recent_messages=[
            {"role": "assistant", "content": "进入 Context Binding 以后，核心中间产物就是 relevant set。"},
            {"role": "assistant", "content": "follow_up、challenge、multi_target 会消费这批 relevant set。"},
        ],
    )

    assert result.binding_snapshot["query_style"] == "standalone"
    assert result.fallback_type == "retrieve_on_raw_query"
    assert result.reason == "query_self_contained"


def test_binding_power_returns_public_typed_binding_result() -> None:
    power = ContextBindingPower()
    result = power.bind("一年期劳动合同试用期上限是多少？", [])
    payload = result.to_dict()

    assert isinstance(result, ContextBindingResult)
    assert "binding_snapshot" in payload
    assert "relevant_set" in payload
    assert "fallback_type" in payload


def test_context_binding_power_no_longer_uses_dialogue_state_focus_continuity() -> None:
    source = ContextBindingPower.bind.__code__.co_varnames

    assert "dialogue_state" not in source


def test_binding_snapshot_exposes_source_counts_and_fallback_observability() -> None:
    power = ContextBindingPower()
    memory = _working_memory(
        WorkingMemoryEntry(
            entry_id="wm_answer_1",
            entry_type="answer_unit",
            turn_id="turn_1",
            source_kind="answer",
            source_ref="turn_1:answer:1",
            content="relevant set 仍然是规则第一版。",
            confidence="high",
        ),
        WorkingMemoryEntry(
            entry_id="wm_answer_2",
            entry_type="answer_unit",
            turn_id="turn_2",
            source_kind="answer",
            source_ref="turn_2:answer:1",
            content="working memory writer 仍然偏粗。",
            confidence="high",
        ),
    )

    def fake_llm_call(prompt: str) -> str:
        assert "候选相关对象" in prompt
        return '{"resolved_target_ids":[],"rewritten_query":"","confidence":"low","needs_clarification":true,"fallback_type":"needs_clarification","reason":"multiple_relevant_targets"}'

    result = power.bind(
        "这个呢？",
        [{"object_id": "candidate_recent", "object_type": "question_object", "content": "最近候选对象", "source_kind": "registry"}],
        working_memory=memory,
        llm_call=fake_llm_call,
        recent_messages=[{"role": "user", "content": "我们刚才讨论 relevant set 和 writer。"}],
    )

    assert result.binding_snapshot["candidate_pool_size"] >= 1
    assert result.binding_snapshot["candidate_source_counts"]["registry"] == 1
    assert result.binding_snapshot["relevant_source_counts"]["answer"] >= 1
    assert result.binding_snapshot["fallback_type"] == "needs_clarification"
    assert result.binding_snapshot["fallback_reason"] == "multiple_relevant_targets"
