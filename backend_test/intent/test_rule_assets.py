from __future__ import annotations

from intent.rule_assets import (
    DOMAIN_BOOTSTRAP_CONFIG_PATH,
    DOMAIN_HINT_TOKENS,
    DOMAIN_QA_PATTERNS,
    SELF_ANCHOR_TOKENS,
    load_domain_bootstrap_assets,
)


def test_domain_bootstrap_assets_load_from_config() -> None:
    assets = load_domain_bootstrap_assets()

    assert DOMAIN_BOOTSTRAP_CONFIG_PATH.name == "domain_bootstrap_rules.json"
    assert assets.version == "1.0.0"
    assert assets.asset_group == "domain_bootstrap"
    assert assets.scope == "group_shared"
    assert assets.domain_qa_patterns
    assert assets.domain_actor_patterns
    assert "合同" in assets.domain_hint_tokens
    assert "责任" in assets.self_anchor_tokens


def test_loaded_domain_bootstrap_assets_keep_expected_negative_noise_out() -> None:
    assert "代码解析" not in DOMAIN_HINT_TOKENS
    assert "随便聊聊" not in SELF_ANCHOR_TOKENS
    assert not any(pattern.search("今天心情一般") for pattern in DOMAIN_QA_PATTERNS)
