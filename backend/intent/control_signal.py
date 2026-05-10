from __future__ import annotations

from intent.types import ControlSignal, IntentResult


def build_control_signal(
    intent: IntentResult,
    *,
    force_qa_citation: bool = True,
) -> ControlSignal:
    """Convert recognition output into stable execution control flags."""

    modifiers = intent.modifiers

    if modifiers.out_of_scope:
        return ControlSignal(route="reject")

    if modifiers.needs_clarification:
        return ControlSignal(route="direct", mode="clarify")

    if modifiers.ask_capability:
        return ControlSignal(route="direct", mode="capability")

    if intent.main_intent == "chat":
        return ControlSignal(route="chat")

    if modifiers.challenge:
        return ControlSignal(
            route="rag",
            rewrite=True,
            mode="challenge",
            force_citation=True,
        )

    return ControlSignal(
        route="rag",
        rewrite=modifiers.follow_up,
        mode="normal",
        force_citation=force_qa_citation or modifiers.ask_source,
    )
