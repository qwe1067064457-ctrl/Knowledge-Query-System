# Rule Lite 收缩清单 V1

## 目标

- 让 `rule` 层回到 `baseline / teacher / guardrail`
- 让 `evidence` 主要表达“看到了什么”
- 让 `resolver` 主要表达“最终理解成什么”
- 让 `control` 只消费 `resolved`，不反向污染 understanding

## Rule 保留职责

- `unsupported / safety`
- `system / capability / scope` 粗识别
- `qa / chat / system / unsupported` 粗分类
- `follow_up / ask_source / challenge / soft_doubt` 粗识别
- `baseline / teacher / regression anchor`

## Rule 收缩职责

- 不再强扛 `clarify` 最终裁决
- 不再强扛细粒度 `task` 终判
- 不再把“回答结构”直接解释成“执行步骤”
- 不再过早承诺 `decomposition / planner / workflow` 细节

## Evidence 结构

### request semantic signals

- `follow_up`
- `ask_source`
- `challenge`
- `soft_doubt`
- `scope_question`

### context fact signals

- `history_reference`
- `needs_previous_answer`
- `previous_retrieval`
- `missing_reference_target`
- `possibly_ambiguous`
- `needs_context_check`

### buckets

- `intent`
- `task`
- `context_fact`
- `safety`

## Resolver 结构

- `main_intent`
- `modifiers`
- `task`
  - `complexity`
  - `shape`
  - `topology`
  - `answer_shape_hint`
- `context_dependency`
- `ambiguity_state`

## 兼容策略

- `ask_capability` 保留作兼容字段，逐步收敛到 `scope_question`
- `needs_clarification` 保留作兼容字段，逐步收敛到 `clarify_candidate / ambiguity_state`
- `signal_buckets.context` 在兼容层保留，但 `V2` 新口径按 `context_fact` 理解
- `ask_source / challenge / soft_doubt` 不再允许双角色落桶：
  - 主职责只在 `intent`
  - 相关上下文依赖改由 `context_fact` 表达

## 模式设计

- `rule_only`
  - baseline
  - hard gate
  - 冷启动
  - 回归基线
- `rule_plus_model`
  - 近期主路线
  - rule 做 coarse understanding 与 guardrail
  - model 做中层收敛增强
- `model_first_rule_guard`
  - 远期目标
  - model 先理解
  - rule 只做边界与安全守卫

## 审核重点

- 是否继续出现一个 signal 同时承担请求语义和上下文事实
- 是否继续把 `clarify` 当成 rule 强裁决
- 是否继续把“回答结构要求”误判成 `staged`
- 是否继续让 `complex` 过早绑定高消耗执行路径
status: active-working
related_current_doc: notes/intent/intent_rule_lite_strategy.md
scope: rule-lite shrink checklist
