from __future__ import annotations

from llm.output_sanitizer import StreamingReasoningFilter, sanitize_model_text


def test_sanitize_model_text_removes_think_block() -> None:
    raw = "<think>internal reasoning</think>\n最终答案"
    assert sanitize_model_text(raw) == "最终答案"


def test_sanitize_model_text_keeps_plain_text() -> None:
    raw = "这是正常输出。"
    assert sanitize_model_text(raw) == "这是正常输出。"


def test_streaming_reasoning_filter_hides_split_think_block() -> None:
    stream = StreamingReasoningFilter()
    first = stream.feed("<thi")
    second = stream.feed("nk>internal")
    third = stream.feed(" reasoning</thi")
    fourth = stream.feed("nk>最终")
    fifth = stream.feed("答案")
    tail = stream.flush()

    assert first == ""
    assert second == ""
    assert third == ""
    assert fourth == "最终"
    assert fifth == "答案"
    assert tail == ""
