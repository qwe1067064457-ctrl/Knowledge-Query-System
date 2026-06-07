# Context Binding V2 Architecture

## 正式定位

`Context Binding` 不是“唯一恢复 query 真正指代对象”的系统。

它的正式定位是：

- 判断当前 query 是否依赖上下文
- 从多源候选中构造 `relevant pool`
- 把 `relevant pool` 压缩成小型 `relevant set`
- 让主大模型完成最终 `resolution / rewrite / clarification`
- 在无法稳定解析时返回结构化 fallback

## 主链

正式主链如下：

`query -> query style -> relevant pool -> relevant set -> rule direct / llm resolution / fallback`

## 数据来源

`relevant pool` 只保留 3 类来源：

- recent candidates
- session working memory
- optional memory anchors

旧 `dialogue_state` 不再进入 relevant pool。

## 与其他模块的边界

- `workflow/policy`
  - 决定 route / handling mode / 是否启用 context binding
- `ContextBindingPower`
  - 决定 relevant set、rewrite、resolution、fallback
- `binding_worker`
  - 只做规则筛选，不做最终 truth-like target 判定
- `Session Working Memory`
  - 只做 short-term semantic candidate pool
- `memory anchor / context_hydrator`
  - 只做 long-term memory hit 后的上下文回锚与补水
