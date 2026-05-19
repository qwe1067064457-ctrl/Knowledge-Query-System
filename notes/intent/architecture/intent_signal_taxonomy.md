# Intent Signal Taxonomy

## 1. 为什么要重构 signal taxonomy

旧问题不是 signal 不够多，而是：

- 某些 signal 职责混杂
- 同一个 signal 同时承担“请求语义”和“上下文事实”
- evidence 层越来越难解释

最典型的例子就是：

- `ask_source`
- `challenge`
- `soft_doubt`

它们过去经常同时承担：

1. 这是什么请求
2. 它依赖什么上下文

现在的目标是把这两件事拆开。

## 2. 当前推荐 taxonomy

当前稳定方向是四桶：

- `intent`
- `task`
- `context_fact`
- `safety`

## 3. 各桶定义

### 3.1 `intent`

回答：

> 这个请求在语义上是在做什么？

适合放这里的 signal：

- `ask_source`
- `challenge`
- `soft_doubt`
- `follow_up`
- `scope_question`

它们表达的是：

- 请求语义
- 请求动作
- 用户此刻在问什么类型的问题

### 3.2 `task`

回答：

> 这个请求的任务结构和任务形态是什么？

适合放这里的 signal：

- `multi_question`
- `parallel_subtasks`
- `staged`
- `complex_task`
- `compare_hint`
- `verify_hint`
- `summarize_hint`

### 3.3 `context_fact`

回答：

> 正确理解这个请求时，依赖了什么上下文事实，或者缺了什么上下文事实？

这不是意图修饰，而是：

- 当前理解所需的上下文条件
- 或当前缺失的上下文条件

推荐 signal：

- `needs_previous_answer`
- `history_reference`
- `missing_reference_target`
- `possibly_ambiguous`
- `needs_context_check`

### 3.4 `safety`

回答：

> 这是不是高风险、越权或不支持请求？

适合放这里的 signal：

- `unsupported`
- `out_of_scope`
- `privileged_operation`
- `destructive_request`

## 4. request semantic vs context fact

这是 V2 最重要的拆分之一。

### `request semantic`

表达的是：

- 用户在做什么请求动作

例如：

- `ask_source`
- `challenge`
- `soft_doubt`

### `context fact`

表达的是：

- 当前 query 的理解依赖了什么上下文
- 或当前缺什么上下文

例如：

- `needs_previous_answer`
- `missing_reference_target`

### 为什么要拆

否则会一直出现这种问题：

- signal 命中了，但你说不清它到底命中了什么
- quality gate 很难定义
- resolver 很难稳定收敛

## 5. 示例

### 示例 1：`依据是什么？`

更干净的表示应该是：

- `intent`
  - `ask_source`
- `context_fact`
  - `needs_previous_answer`
  - `missing_reference_target`

而不是：

- `ask_source` 同时扮演请求语义和上下文依赖

### 示例 2：`你确定吗？`

更干净的表示应该是：

- `intent`
  - `challenge`
- `context_fact`
  - `needs_previous_answer`
  - `possibly_ambiguous`

### 示例 3：`这个规则全国都适用吗？`

它可能是：

- `intent`
  - `qa`
- `context_fact`
  - `needs_context_check`
  - 可选 `possibly_ambiguous`

重点在于：

- 不要因为出现了“这个”就直接把它写死成最终 clarify

## 6. 当前还处在迁移中的部分

当前主设计已经转向 `context_fact`，但兼容层里仍可能看到旧口径：

- `context`
- 双角色 signal

这属于迁移期现象，不代表长期主设计。

## 7. 使用原则

### 原则 1：一个 signal 尽量只承担一个主职责

### 原则 2：请求语义和上下文事实分开建模

### 原则 3：signal 只提供理解证据，不直接等于执行动作

### 原则 4：quality gate 要同时检查

- bucket 是否合理
- signal 是否异常迁移
- 新旧 signal 是否符合迁移预期

## 8. 一句话总结

当前 signal taxonomy 的核心变化是：

> 不再让同一个 signal 同时表示“这是什么请求”和“它依赖什么上下文”，而是把请求语义与上下文事实拆开，收口到 `intent / task / context_fact / safety` 四桶。 
