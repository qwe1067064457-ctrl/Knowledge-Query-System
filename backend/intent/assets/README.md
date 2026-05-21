# Intent Assets

`assets/*.json` 用来承载 group-scoped 的 intent 知识性规则资产。

约定：

- 一个资产组对应一个 JSON 文件，例如 `law.json`、`medical.json`
- `storage/groups/{group_id}/meta.json` 只负责选择 `memory_policy.intent.asset_group`
- 稳定的结构性规则不要放在这里，例如寒暄、能力询问、通用 follow-up 识别
- 依赖具体领域知识的模式、词表、judgment anchor 要放在这里

当前统一字段：

- `domain_qa_patterns`
- `domain_actor_patterns`
- `domain_hint_tokens`
- `self_anchor_tokens`
- `judgment_anchor_patterns`
- `missing_history_block_patterns`
- `judgment_clarify_exempt_patterns`
- `complex_qa_anchor_patterns`
