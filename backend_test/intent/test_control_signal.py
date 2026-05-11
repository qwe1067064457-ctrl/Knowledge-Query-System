from __future__ import annotations

from intent import build_control_signal
from intent.types import IntentModifiers, IntentResult


def test_qa_routes_to_rag_with_citation_by_default() -> None:
    signal = build_control_signal(IntentResult(main_intent="qa"))

    assert signal.route == "rag"
    assert signal.mode == "normal"
    assert signal.rewrite is False
    assert signal.force_citation is True


def test_follow_up_qa_requires_rewrite() -> None:
    intent = IntentResult(
        main_intent="qa",
        modifiers=IntentModifiers(follow_up=True),
    )

    signal = build_control_signal(intent)

    assert signal.route == "rag"
    assert signal.rewrite is True
    assert signal.mode == "normal"


def test_challenge_forces_rag_rewrite_and_citation() -> None:
    intent = IntentResult(
        main_intent="qa",
        modifiers=IntentModifiers(challenge=True, ask_source=True),
    )

    signal = build_control_signal(intent)

    assert signal.route == "rag"
    assert signal.rewrite is True
    assert signal.mode == "challenge"
    assert signal.force_citation is True


def test_chat_routes_to_chat() -> None:
    signal = build_control_signal(IntentResult(main_intent="chat"))

    assert signal.route == "chat"
    assert signal.mode == "normal"
    assert signal.force_citation is False


def test_capability_request_routes_to_direct_capability() -> None:
    intent = IntentResult(
        main_intent="chat",
        modifiers=IntentModifiers(ask_capability=True),
    )

    signal = build_control_signal(intent)

    assert signal.route == "direct"
    assert signal.mode == "capability"


def test_unclear_meta_routes_to_clarify() -> None:
    intent = IntentResult(
        main_intent="chat",
        modifiers=IntentModifiers(needs_clarification=True),
    )

    signal = build_control_signal(intent)

    assert signal.route == "direct"
    assert signal.mode == "clarify"


def test_out_of_scope_routes_to_reject() -> None:
    intent = IntentResult(
        main_intent="chat",
        modifiers=IntentModifiers(out_of_scope=True),
    )

    signal = build_control_signal(intent)

    assert signal.route == "reject"
    assert signal.mode == "normal"
