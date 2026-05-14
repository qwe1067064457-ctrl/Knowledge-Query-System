from __future__ import annotations

import json
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Pattern


def _compile_patterns(patterns: tuple[str, ...]) -> tuple[Pattern[str], ...]:
    return tuple(re.compile(pattern, re.IGNORECASE) for pattern in patterns)


@dataclass(frozen=True)
class DomainBootstrapAssets:
    version: str
    asset_group: str
    scope: str
    description: str
    last_updated: str
    domain_qa_patterns: tuple[Pattern[str], ...]
    domain_actor_patterns: tuple[Pattern[str], ...]
    domain_hint_tokens: tuple[str, ...]
    self_anchor_tokens: tuple[str, ...]


DOMAIN_BOOTSTRAP_CONFIG_PATH = Path(__file__).with_name("domain_bootstrap_rules.json")


@lru_cache(maxsize=1)
def load_domain_bootstrap_assets() -> DomainBootstrapAssets:
    payload = json.loads(DOMAIN_BOOTSTRAP_CONFIG_PATH.read_text(encoding="utf-8"))
    assets = payload["assets"]
    return DomainBootstrapAssets(
        version=str(payload["version"]),
        asset_group=str(payload["asset_group"]),
        scope=str(payload["scope"]),
        description=str(payload["description"]),
        last_updated=str(payload["last_updated"]),
        domain_qa_patterns=_compile_patterns(tuple(assets["domain_qa_patterns"])),
        domain_actor_patterns=_compile_patterns(tuple(assets["domain_actor_patterns"])),
        domain_hint_tokens=tuple(assets["domain_hint_tokens"]),
        self_anchor_tokens=tuple(assets["self_anchor_tokens"]),
    )


# Stable global rules: these should remain valid even when the KB domain changes.
ASK_SOURCE_PATTERNS = _compile_patterns(
    (
        r"依据是什么|依据呢|什么依据|有依据吗|为什么这么说",
        r"来源|出处|引用|证据|司法解释|法条依据|条文依据",
        r"哪一条|哪条|哪个文件|哪份资料|哪部司法解释",
        r"\b(source|citation|reference)\b",
    )
)

CHALLENGE_PATTERNS = _compile_patterns(
    (
        r"你(确定|肯定)吗|确定吗",
        r"(不对吧|不正确|错了|错误|有问题|不严谨|瞎说|胡说|乱说)",
        r"是不是.{0,10}(错|不对|有问题|搞错了)",
        r"你刚才.{0,12}(不对|错|矛盾|不一致|说反了|搞错了)",
        r"(和|跟).{0,12}(不一致|矛盾|冲突)",
        r"(理解错了|漏掉了?限制条件)",
        r"(并不|不太|并不觉得).{0,8}(对|准确|严谨|合理)",
    )
)

CAPABILITY_PATTERNS = _compile_patterns(
    (
        r"你能做什么|你可以做什么|能干什么",
        r"有什么功能|支持什么|怎么用",
        r"你是谁|介绍一下你自己",
    )
)

FOLLOW_UP_PATTERNS = _compile_patterns(
    (
        r"^(那|那么|如果|要是|这种|这个|上述|刚才|前面)",
        r"(这种情况|这个情况|那种情况|上述情况|刚才说的|前面说的)",
        r"^(继续|还有吗|还有呢|再说|展开说)",
        r"(它|这个|那个|上述|前者|后者).{0,8}(呢|吗|如何|怎么|是否|多久|多少)",
    )
)

CHAT_PATTERNS = _compile_patterns(
    (
        r"^(你好|您好|嗨|hello|hi)[！!。,.，\s]*$",
        r"^(谢谢|感谢|辛苦了|好的|明白了)[！!。,.，\s]*$",
    )
)

JUDGMENT_QA_PATTERNS = _compile_patterns(
    (
        r"(算不算|是否|合理吗|合规吗|合法吗|违法吗|有责任吗|怎么赔|赔多少|怎么处理)",
    )
)

META_ANALYSIS_QA_PATTERNS = _compile_patterns(
    (
        r"(代码|规则|分类器|classifier|resolver|control).{0,10}(怎么判断|如何判断|怎么分流|如何分流|怎么识别|如何识别)",
        r"(看|按).{0,8}(代码|规则).{0,12}(解析|判断|分流|识别)",
        r"(这个|该).{0,4}(query|问题|输入).{0,12}(能|会).{0,8}(怎么判断|怎么分流|怎么识别|分到哪里)",
        r"(当前|现在).{0,4}(规则|分类器).{0,12}(能不能|是否能|会不会).{0,8}(判断|识别|分流)",
    )
)


_DOMAIN_BOOTSTRAP = load_domain_bootstrap_assets()

DOMAIN_QA_PATTERNS = _DOMAIN_BOOTSTRAP.domain_qa_patterns
DOMAIN_ACTOR_PATTERNS = _DOMAIN_BOOTSTRAP.domain_actor_patterns
DOMAIN_HINT_TOKENS = _DOMAIN_BOOTSTRAP.domain_hint_tokens
SELF_ANCHOR_TOKENS = _DOMAIN_BOOTSTRAP.self_anchor_tokens
