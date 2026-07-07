# Decomposition Runtime Skill

## 作用

把明显多子问题请求拆成 query unit，并保留依赖边。

## 何时使用

- 明确多问并列
- staged/parallel 结构明显

## 何时不要使用

- 单问句
- 长但边界不清的请求

## 流程

1. question boundary detector
2. dependency resolver
3. sub-question rewrite
4. `query_unit_builder`

## 输出契约

返回 `DecompositionSkillResult`。

## 失败兜底

- 边界不清时退回 `single_unit`
