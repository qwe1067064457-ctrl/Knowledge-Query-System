# Context Binding V2 Contracts

## Query Style

`Query Style` 只服务 `context binding / relevant set` 层。

当前分类：

- `challenge`
- `follow_up`
- `multi_target`
- `standalone`

它回答的是：

- 当前 query 在上下文依赖形态上像什么
- relevant set 应该优先保留哪些对象类型

## Handling Mode

`Handling Mode` 仍归 workflow/policy 层。

它回答的是：

- 当前整轮请求应该按什么整体处理策略执行

典型值包括：

- `challenge`
- `clarify`
- `scope_info`
- `unsupported`

## ContextBindingResult

正式输出字段：

- `relevant_set`
- `resolved_target_ids`
- `rewritten_query`
- `binding_confidence`
- `needs_clarification`
- `fallback_type`
- `reason`
- `binding_snapshot`

说明：

- `binding_snapshot` 是局部 resolution 快照
- 它不是 `session working memory`
- 它也不是历史 owner
