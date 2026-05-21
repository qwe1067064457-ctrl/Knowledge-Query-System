from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

from intent.loaders import (
    DEFAULT_ASSET_GROUP,
    DOMAIN_BOOTSTRAP_CONFIG_PATH,
    load_group_intent_rule_assets,
    load_intent_rule_assets,
    resolve_group_asset_group,
)


def test_domain_bootstrap_assets_load_from_config() -> None:
    assets = load_intent_rule_assets()

    assert DOMAIN_BOOTSTRAP_CONFIG_PATH.name == "domain_bootstrap.json"
    assert assets.version == "1.1.0"
    assert assets.asset_group == DEFAULT_ASSET_GROUP
    assert assets.scope == "group_shared"
    assert assets.domain_qa_patterns
    assert assets.domain_actor_patterns
    assert assets.judgment_anchor_patterns
    assert "合同" in assets.domain_hint_tokens
    assert "责任" in assets.self_anchor_tokens


def test_unknown_asset_group_falls_back_to_empty_isolated_profile() -> None:
    assets = load_intent_rule_assets("general")

    assert assets.asset_group == "general"
    assert assets.domain_qa_patterns == ()
    assert assets.domain_hint_tokens == ()
    assert assets.self_anchor_tokens == ()


def test_group_intent_assets_use_group_policy_override() -> None:
    base_storage = Path(".test_tmp") / f"group-assets-{uuid4().hex}" / "storage"
    group_dir = base_storage / "groups" / "general"
    group_dir.mkdir(parents=True, exist_ok=True)
    (group_dir / "meta.json").write_text(
        json.dumps(
            {
                "id": "general",
                "memory_policy": {
                    "intent": {
                        "asset_group": "general",
                    }
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    assert resolve_group_asset_group(base_storage, "general") == "general"

    assets = load_group_intent_rule_assets(base_storage, "general")
    assert assets.asset_group == "general"
    assert assets.domain_hint_tokens == ()


def test_group_intent_assets_default_to_bootstrap_without_policy() -> None:
    base_storage = Path(".test_tmp") / f"group-assets-{uuid4().hex}" / "storage"
    group_dir = base_storage / "groups" / "law"
    group_dir.mkdir(parents=True, exist_ok=True)
    (group_dir / "meta.json").write_text(
        json.dumps({"id": "law", "memory_policy": {}}, ensure_ascii=False),
        encoding="utf-8",
    )

    assets = load_group_intent_rule_assets(base_storage, "law")

    assert assets.asset_group == DEFAULT_ASSET_GROUP
    assert any(pattern.search("劳动合同法中试用期最长多久？") for pattern in assets.domain_qa_patterns)
