from __future__ import annotations

from dataclasses import dataclass
from typing import Pattern


@dataclass(frozen=True)
class IntentRuleAssets:
    version: str
    asset_group: str
    scope: str
    description: str
    last_updated: str
    domain_qa_patterns: tuple[Pattern[str], ...]
    domain_actor_patterns: tuple[Pattern[str], ...]
    domain_hint_tokens: tuple[str, ...]
    self_anchor_tokens: tuple[str, ...]
    judgment_anchor_patterns: tuple[Pattern[str], ...]
    missing_history_block_patterns: tuple[Pattern[str], ...]
    judgment_clarify_exempt_patterns: tuple[Pattern[str], ...]
    complex_qa_anchor_patterns: tuple[Pattern[str], ...]
