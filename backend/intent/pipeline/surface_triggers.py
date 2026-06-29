from __future__ import annotations

from intent.schema.intent_types import RuleMatch


def surface_trigger_ids(matches: tuple[RuleMatch, ...]) -> tuple[str, ...]:
    """Return stable ids for keyword/pattern hits without judging trust."""

    return tuple(match.rule_id for match in matches)

