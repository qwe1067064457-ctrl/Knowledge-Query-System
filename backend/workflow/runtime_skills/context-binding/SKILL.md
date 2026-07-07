# Context Binding Runtime Skill

## 作用

把上下文相关问句收敛成可执行的改写或澄清结果。

## 何时使用

- follow-up
- 指代或省略明显
- 需要回答侧恢复引用对象

## 何时不要使用

- 独立单轮问题
- 已经有明确 target 的 query unit

## 流程

1. `candidate_collection`
2. Relevant set 语义筛选
3. Target resolution 裁决
4. `query_rewrite`

## 输出契约

返回 `ContextBindingSkillResult`。

## 失败兜底

- ambiguous -> `needs_clarification`
- no target -> `rewrite_without_target`
