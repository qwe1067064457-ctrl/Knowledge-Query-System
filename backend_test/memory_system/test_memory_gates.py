from __future__ import annotations

from memory_system.extraction import CoreGate, DailyLogGate, DomainCaseGate


def test_core_gate_selects_only_messages_with_explicit_markers() -> None:
    gate = CoreGate()
    selected = gate.select_candidate_messages(
        [
            {"role": "user", "content": "以后默认使用中文回答。"},
            {"role": "user", "content": "今天天气不错。"},
            {"role": "assistant", "content": "默认使用中文回答。"},
        ],
        explicit_markers=["以后", "默认"],
    )

    assert len(selected) == 1
    assert selected[0]["content"] == "以后默认使用中文回答。"


def test_daily_log_gate_rejects_when_checkpoint_disabled() -> None:
    gate = DailyLogGate()

    result = gate.should_extract(
        checkpoint_enabled=False,
        messages=[{"role": "user", "content": "本轮确认了 challenge path。"}],
        compaction_summary="",
    )

    assert result is False


def test_domain_case_gate_requires_completed_structured_material() -> None:
    gate = DomainCaseGate()

    assert gate.should_extract(
        messages=[{"role": "assistant", "content": "ISSUE: breach. ANALYSIS: compare. CONCLUSION: keep. DONE."}],
        compaction_summary="",
        looks_like_completed_result=lambda text: "DONE" in text,
        looks_like_case_body=lambda text: "ISSUE" in text and "CONCLUSION" in text,
    ) is True
    assert gate.should_extract(
        messages=[{"role": "assistant", "content": "DONE. short answer."}],
        compaction_summary="",
        looks_like_completed_result=lambda text: "DONE" in text,
        looks_like_case_body=lambda text: "ISSUE" in text and "CONCLUSION" in text,
    ) is False
