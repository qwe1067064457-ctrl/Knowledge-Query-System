from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from intent.loaders.asset_loader import DEFAULT_ASSET_GROUP, load_intent_rule_assets
from intent.schema.asset_types import IntentRuleAssets


INTENT_POLICY_KEY = "intent"
INTENT_ASSET_GROUP_KEY = "asset_group"


def _group_meta_path(base_storage_path: Path, group_id: str) -> Path:
    return Path(base_storage_path) / "groups" / str(group_id) / "meta.json"


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def resolve_group_asset_group(
    base_storage_path: Path,
    group_id: str,
    *,
    default_asset_group: str = DEFAULT_ASSET_GROUP,
) -> str:
    group_meta = _read_json(_group_meta_path(Path(base_storage_path), group_id))
    memory_policy = group_meta.get("memory_policy", {})
    if not isinstance(memory_policy, dict):
        return default_asset_group
    intent_policy = memory_policy.get(INTENT_POLICY_KEY, {})
    if not isinstance(intent_policy, dict):
        return default_asset_group
    asset_group = intent_policy.get(INTENT_ASSET_GROUP_KEY)
    if not asset_group:
        return default_asset_group
    return str(asset_group)


def load_group_intent_rule_assets(
    base_storage_path: Path,
    group_id: str,
    *,
    default_asset_group: str = DEFAULT_ASSET_GROUP,
) -> IntentRuleAssets:
    asset_group = resolve_group_asset_group(
        base_storage_path,
        group_id,
        default_asset_group=default_asset_group,
    )
    return load_intent_rule_assets(asset_group)
