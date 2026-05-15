# user_batch_v1

这批数据直接来自本轮讨论中的 8 类 query，目标不是回归已有规则，而是用更贴近真实表达的输入去压测 `input -> evidence -> resolved -> control` 四层识别效果。

批次包括：
- `standard_qa`
- `fuzzy_qa`
- `chat`
- `meta`
- `follow_up`
- `mixed_intent`
- `adversarial`
- `long_case_complex`

其中：
- `standard_qa` 主要测清晰问答
- `fuzzy_qa` 主要测 `needs_clarification`
- `mixed_intent` 主要测 modifier 组合与 resolver 收敛
- `adversarial` 主要测 challenge 稳健性
- `long_case_complex` 主要测复杂事实输入是否会掉进简单流
