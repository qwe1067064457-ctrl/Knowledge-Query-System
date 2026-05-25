# Context Binding Trigger And Scope

## 定位

`context binding` 不是“唯一恢复 query 真正指代对象”的模块。

它的正式定位是：

- `query rewrite / context resolution`
- relevant set 筛选 owner
- 在需要时把 query 补全到可检索、可 challenge、可澄清的状态

## 什么时候触发

不是每轮都触发。

只在这些场景触发：

- follow-up
- 指代
- 省略
- challenge
- answer side 引用恢复
- memory hit 后需要补上下文

## 不应该触发的场景

- 独立完整 query
- 纯表达型任务
- scope 未明确且应先澄清

## 输入

- recent conversation
- `Session Working Memory`
- registry candidates
- optional memory anchors

## 输出

- relevant set
- resolved target ids
- rewritten query
- binding confidence
- fallback contract

