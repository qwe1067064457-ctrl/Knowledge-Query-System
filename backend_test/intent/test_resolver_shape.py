from __future__ import annotations

from intent.resolver import resolve_intent
from intent.types import IntentEvidence, SignalBuckets, TaskCandidate


def _evidence(*task_candidates: TaskCandidate) -> IntentEvidence:
    return IntentEvidence(
        classifier_mode="rule_plus_model",
        signal_buckets=SignalBuckets(intent=("qa",), task=(), context=(), safety=()),
        candidate_intents=(),
        task_candidates=task_candidates,
    )


def test_resolver_returns_mixed_only_for_two_strong_complex_shapes() -> None:
    evidence = _evidence(
        TaskCandidate(complexity="complex", shape="compare", score=0.82, topology="single"),
        TaskCandidate(complexity="complex", shape="summarize", score=0.8, topology="single"),
    )

    resolved = resolve_intent(evidence)

    assert resolved.task.complexity == "complex"
    assert resolved.task.shape == "mixed"


def test_resolver_prefers_named_shape_over_single_question_fallback() -> None:
    evidence = _evidence(
        TaskCandidate(complexity="complex", shape="single_question", score=0.8, topology="single"),
        TaskCandidate(complexity="complex", shape="verify", score=0.74, topology="single"),
    )

    resolved = resolve_intent(evidence)

    assert resolved.task.complexity == "complex"
    assert resolved.task.shape == "verify"


def test_resolver_keeps_single_question_when_no_named_complex_shape_exists() -> None:
    evidence = _evidence(
        TaskCandidate(complexity="complex", shape="single_question", score=0.8, topology="single"),
    )

    resolved = resolve_intent(evidence)

    assert resolved.task.complexity == "complex"
    assert resolved.task.shape == "single_question"
