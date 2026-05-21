from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Pattern

from intent.schema.asset_types import IntentRuleAssets


DEFAULT_ASSET_GROUP = "domain_bootstrap"
ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"
DOMAIN_BOOTSTRAP_CONFIG_PATH = ASSETS_DIR / "domain_bootstrap.json"


def _compile_patterns(patterns: tuple[str, ...]) -> tuple[Pattern[str], ...]:
    return tuple(re.compile(pattern, re.IGNORECASE) for pattern in patterns)


def _coerce_text_tuple(payload: Any) -> tuple[str, ...]:
    if not isinstance(payload, list):
        return ()
    return tuple(str(item) for item in payload if str(item).strip())


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Intent asset file not found: {path}")
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"Intent asset file must be a JSON object: {path}")
    return payload


def _asset_file_path(asset_group: str) -> Path:
    safe_group = str(asset_group or DEFAULT_ASSET_GROUP).strip() or DEFAULT_ASSET_GROUP
    if safe_group == DEFAULT_ASSET_GROUP:
        return DOMAIN_BOOTSTRAP_CONFIG_PATH
    return ASSETS_DIR / f"{safe_group}.json"


def _empty_assets(asset_group: str) -> IntentRuleAssets:
    return IntentRuleAssets(
        version="1.0.0",
        asset_group=asset_group,
        scope="group_scoped",
        description=f"Intent rule assets for '{asset_group}' with no domain knowledge anchors.",
        last_updated="",
        domain_qa_patterns=(),
        domain_actor_patterns=(),
        domain_hint_tokens=(),
        self_anchor_tokens=(),
        judgment_anchor_patterns=(),
        missing_history_block_patterns=(),
        judgment_clarify_exempt_patterns=(),
        complex_qa_anchor_patterns=(),
    )


@lru_cache(maxsize=32)
def load_intent_rule_assets(asset_group: str = DEFAULT_ASSET_GROUP) -> IntentRuleAssets:
    normalized_group = str(asset_group or DEFAULT_ASSET_GROUP).strip() or DEFAULT_ASSET_GROUP
    path = _asset_file_path(normalized_group)
    if not path.exists():
        if normalized_group == DEFAULT_ASSET_GROUP:
            raise FileNotFoundError(f"Default intent asset group is missing: {path}")
        return _empty_assets(normalized_group)

    payload = _read_json(path)
    assets = payload.get("assets", {})
    if not isinstance(assets, dict):
        raise ValueError(f"Intent asset file has invalid assets section: {path}")

    return IntentRuleAssets(
        version=str(payload.get("version", "1.0.0")),
        asset_group=str(payload.get("asset_group", normalized_group)),
        scope=str(payload.get("scope", "group_scoped")),
        description=str(payload.get("description", "")),
        last_updated=str(payload.get("last_updated", "")),
        domain_qa_patterns=_compile_patterns(_coerce_text_tuple(assets.get("domain_qa_patterns"))),
        domain_actor_patterns=_compile_patterns(_coerce_text_tuple(assets.get("domain_actor_patterns"))),
        domain_hint_tokens=_coerce_text_tuple(assets.get("domain_hint_tokens")),
        self_anchor_tokens=_coerce_text_tuple(assets.get("self_anchor_tokens")),
        judgment_anchor_patterns=_compile_patterns(_coerce_text_tuple(assets.get("judgment_anchor_patterns"))),
        missing_history_block_patterns=_compile_patterns(_coerce_text_tuple(assets.get("missing_history_block_patterns"))),
        judgment_clarify_exempt_patterns=_compile_patterns(
            _coerce_text_tuple(assets.get("judgment_clarify_exempt_patterns"))
        ),
        complex_qa_anchor_patterns=_compile_patterns(_coerce_text_tuple(assets.get("complex_qa_anchor_patterns"))),
    )


def load_domain_bootstrap_assets() -> IntentRuleAssets:
    return load_intent_rule_assets(DEFAULT_ASSET_GROUP)
