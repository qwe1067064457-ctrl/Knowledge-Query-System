from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal


MainIntent = Literal["qa", "chat"]
Route = Literal["rag", "chat", "direct", "reject"]
Mode = Literal["normal", "challenge", "capability", "clarify"]


@dataclass(frozen=True)
class IntentModifiers:
    follow_up: bool = False
    challenge: bool = False
    ask_source: bool = False
    ask_capability: bool = False
    needs_clarification: bool = False
    out_of_scope: bool = False

    def to_dict(self) -> dict[str, bool]:
        return asdict(self)


@dataclass(frozen=True)
class IntentResult:
    main_intent: MainIntent
    modifiers: IntentModifiers = field(default_factory=IntentModifiers)
    matched_signals: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "main_intent": self.main_intent,
            "modifiers": self.modifiers.to_dict(),
            "matched_signals": list(self.matched_signals),
        }


@dataclass(frozen=True)
class ControlSignal:
    route: Route
    rewrite: bool = False
    mode: Mode = "normal"
    force_citation: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
