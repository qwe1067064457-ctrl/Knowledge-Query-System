from __future__ import annotations

from memory_system.session_working_memory.writer import SessionWorkingMemoryWriter


def test_writer_keeps_high_value_answer_units_and_assertions() -> None:
    writer = SessionWorkingMemoryWriter()

    entries = writer.build_entries_from_turn(
        turn_id="turn_1",
        user_query="你刚才这个说法有问题，而且依据不足。",
        answer_text="第一点：working memory 是 short-term semantic candidate pool。第二点：memory anchor 属于 long-term 上下文锚点。",
        current_goal="区分 working memory 和 memory anchor",
        binding_result={
            "rewritten_query": "working memory 和 memory anchor 的区别是什么",
            "binding_confidence": "high",
            "resolved_target_ids": ["wm_answer_1"],
        },
        review_result={"status": "partial_success", "summary": "仍需补充 challenge contract"},
    )

    entry_types = [entry.entry_type for entry in entries]

    assert "focus_task" in entry_types
    assert "resolved_query" in entry_types
    assert entry_types.count("answer_unit") >= 2
    assert "user_assertion" in entry_types
    assert "review_outcome" in entry_types


def test_writer_filters_out_small_talk_and_transitional_answer_units() -> None:
    writer = SessionWorkingMemoryWriter()

    entries = writer.build_entries_from_turn(
        turn_id="turn_2",
        user_query="好的，继续",
        answer_text="如果你愿意，我们继续。下一步我可以先给你一个列表。",
    )

    assert entries == []
