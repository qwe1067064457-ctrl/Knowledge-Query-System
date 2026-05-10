from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict


DEFAULT_CONTEXT_POLICY: Dict[str, Any] = {
    "history": {
        "max_recent_turns": 8,
    },
    "budget": {
        "total_tokens": 6000,
        "core": {
            "reserved": 300,
            "max": 600,
        },
        "retrieved_memories": {
            "target": 800,
            "max": 1400,
        },
        "recent_turns": {
            "target": 2000,
            "max": 3200,
        },
        "tool_results": {
            "target": 400,
            "max": 1000,
            "max_chars_per_message": 4000,
        },
    },
    "compaction": {
        "enabled": True,
        "trigger_ratio": 0.9,
        "keep_recent_tokens": 2000,
    },
    "memory": {
        "search_enabled": True,
        "top_k": 5,
        "time_decay_half_life": 30,
        "use_mmr": True,
        "mmr_lambda": 0.7,
        "flush_enabled": True,
        "flush_threshold": 5400,
    },
    "prompt": {
        "system_prompt_path": "prompts/system_prompt.md",
    },
}


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    merged: Dict[str, Any] = dict(base)
    for key, value in override.items():
        existing = merged.get(key)
        if isinstance(existing, dict) and isinstance(value, dict):
            merged[key] = _deep_merge(existing, value)
        else:
            merged[key] = value
    return merged


def _read_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


class ContextPolicyLoader:
    def __init__(self, policy_path: Path | None = None) -> None:
        self.policy_path = Path(policy_path) if policy_path else Path(__file__).resolve().parent / "context_policy.json"

    def load_policy(self) -> Dict[str, Any]:
        override = _read_json(self.policy_path)
        return _deep_merge(DEFAULT_CONTEXT_POLICY, override)

