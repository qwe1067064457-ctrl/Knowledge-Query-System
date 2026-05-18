from __future__ import annotations

from intent import classify_intent


LAW_HISTORY = [
    {"role": "user", "content": "劳动合同法中试用期最长多久？"},
    {"role": "assistant", "content": "试用期最长可能为六个月，但要看合同期限。"},
]


def test_intent_analysis_grouped_dict_exposes_domain_buckets() -> None:
    result = classify_intent("你刚才的依据是什么？", LAW_HISTORY)

    grouped = result.to_grouped_dict()

    assert set(grouped["evidence"].keys()) == {"meta", "intent", "task", "context", "safety"}
    assert set(grouped["resolved"].keys()) == {"intent", "task", "context", "ambiguity", "decision"}
    assert set(grouped["control"].keys()) == {"dispatch", "policy"}
    assert grouped["resolved"]["intent"]["main_intent"] == "qa"
    assert grouped["control"]["dispatch"]["route"] == "rag"
    assert "ask_source" in grouped["evidence"]["intent"]["raw_signals"]
    assert "needs_previous_answer" in grouped["evidence"]["context"]["raw_signals"]


def test_flat_dict_shape_remains_backward_compatible() -> None:
    result = classify_intent("这样算不算医疗事故？")

    flat = result.to_dict()

    assert "raw_signals" in flat["evidence"]
    assert "signal_buckets" in flat["evidence"]
    assert "candidate_intents" in flat["evidence"]
    assert "context_dependency" in flat["resolved"]
    assert "route" in flat["control"]
    assert "planning_level" in flat["control"]


def test_signal_buckets_flatten_back_to_raw_signals() -> None:
    result = classify_intent("如果没有证据怎么办？")

    assert "needs_context_check" in result.evidence.signal_buckets.context
    assert "needs_context_check" in result.evidence.raw_signals


def test_context_signals_expose_typed_flags() -> None:
    result = classify_intent("你刚才的依据是什么？", LAW_HISTORY)

    context = result.evidence.context_signals

    assert context.needs_previous_answer is True
    assert context.has_previous_intent is True
    assert result.evidence.dependency_signals["previous_answer"] is True


def test_ambiguity_state_exposes_clarify_candidate() -> None:
    result = classify_intent("你确定吗？")

    assert result.resolved.ambiguity_state.clarify_candidate is True
    assert result.resolved.ambiguity_state.needs_context_check is True
    assert result.resolved.ambiguity_state.needs_previous_answer is True
