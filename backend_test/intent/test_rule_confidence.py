from __future__ import annotations

from intent import calculate_rule_confidence
from intent.types import ContextState, RuleMatch


def _rule(rule_id: str, signal: str, strength: str, score: float) -> RuleMatch:
    return RuleMatch(
        rule_id=rule_id,
        signal=signal,
        strength=strength,  # type: ignore[arg-type]
        score=score,
        matched_text="test",
    )


def test_single_high_rule_keeps_high_confidence() -> None:
    confidence = calculate_rule_confidence(
        matched_rules=(
            _rule("challenge.disagree", "challenge", "high", 0.9),
        ),
        raw_signals=("challenge",),
        context_state=ContextState(has_history=True, has_previous_answer=True),
        dependency_signals={
            "none": False,
            "history_reference": False,
            "previous_answer": True,
            "previous_retrieval": False,
            "ambiguous": False,
        },
    )

    assert confidence.final_signal == "challenge"
    assert confidence.final_level == "high"
    assert confidence.final_score >= 0.95
    assert "signal=challenge" in confidence.explanation[0]
    assert "[Final:" in confidence.explanation[0]
    assert "Base(0.90)" in confidence.explanation[0]


def test_same_signal_gets_support_bonus() -> None:
    confidence = calculate_rule_confidence(
        matched_rules=(
            _rule("challenge.disagree", "challenge", "high", 0.9),
            _rule("challenge.confirmation", "challenge", "medium", 0.6),
        ),
        raw_signals=("challenge",),
        context_state=ContextState(has_history=True, has_previous_answer=True),
        dependency_signals={
            "none": False,
            "history_reference": False,
            "previous_answer": True,
            "previous_retrieval": False,
            "ambiguous": False,
        },
    )

    signal_score = confidence.signal_confidences[0]
    assert signal_score.support_bonus == 0.05
    assert signal_score.final_score > signal_score.base_score


def test_conflict_penalty_reduces_signal_score() -> None:
    confidence = calculate_rule_confidence(
        matched_rules=(
            _rule("intent.qa.domain", "qa", "medium", 0.6),
            _rule("intent.chat.greeting", "chat", "high", 0.9),
        ),
        raw_signals=("qa", "chat"),
        context_state=ContextState(),
        dependency_signals={
            "none": True,
            "history_reference": False,
            "previous_answer": False,
            "previous_retrieval": False,
            "ambiguous": False,
        },
    )

    scores = {item.signal: item for item in confidence.signal_confidences}
    assert scores["qa"].conflict_penalty > 0
    assert scores["chat"].conflict_penalty > 0


def test_missing_context_reduces_follow_up_confidence() -> None:
    confidence = calculate_rule_confidence(
        matched_rules=(
            _rule("context.follow_up.reference", "follow_up", "medium", 0.6),
        ),
        raw_signals=("follow_up", "needs_clarification"),
        context_state=ContextState(has_history=False, has_previous_answer=False),
        dependency_signals={
            "none": False,
            "history_reference": False,
            "previous_answer": False,
            "previous_retrieval": False,
            "ambiguous": True,
        },
    )

    signal_score = confidence.signal_confidences[0]
    assert signal_score.context_adjustment < 0
    assert signal_score.level in {"low", "medium"}


def test_explanation_lists_supporting_rules_and_context_term() -> None:
    confidence = calculate_rule_confidence(
        matched_rules=(
            _rule("challenge.disagree", "challenge", "high", 0.9),
            _rule("challenge.confirmation", "challenge", "medium", 0.6),
        ),
        raw_signals=("challenge",),
        context_state=ContextState(has_history=True, has_previous_answer=True),
        dependency_signals={
            "none": False,
            "history_reference": False,
            "previous_answer": True,
            "previous_retrieval": False,
            "ambiguous": False,
        },
    )

    explanation = confidence.explanation[0]
    assert "rules=[challenge.disagree, challenge.confirmation]" in explanation
    assert "Bonus(+0.05)" in explanation
    assert "Context(+0.10)" in explanation


def test_soft_doubt_gets_smaller_context_bonus_than_hard_challenge() -> None:
    confidence = calculate_rule_confidence(
        matched_rules=(
            _rule("challenge.soft_doubt", "soft_doubt", "low", 0.3),
        ),
        raw_signals=("soft_doubt",),
        context_state=ContextState(has_history=True, has_previous_answer=True),
        dependency_signals={
            "none": False,
            "history_reference": False,
            "previous_answer": True,
            "previous_retrieval": False,
            "ambiguous": False,
        },
    )

    signal_score = confidence.signal_confidences[0]
    assert signal_score.context_adjustment == 0.05
