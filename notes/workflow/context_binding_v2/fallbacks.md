# Context Binding Fallbacks

## 原则

找不到对象时，不能只返回“没找到”。

必须返回结构化 fallback。

## fallback 类型

### 1. `needs_clarification`

适用：

- relevant set 为空但 query 明显依赖上下文
- 或 relevant set 里有多个强候选，无法高置信稳定解析

输出：

- `reason`
- `candidate_target_ids`
- `clarification_hint`

### 2. `retrieve_on_raw_query`

适用：

- query 自包含
- 不需要 binding 也可直接检索

输出：

- `reason`
- 原 query 继续下游消费

### 3. `rewrite_without_target`

适用：

- target 不明确
- 但 topic 可以恢复

说明：

- 当前更多是 contract 保留位
- 不是稳定主路径

### 4. `answer_from_context_only`

适用：

- 当前上下文已足够回答
- 不需要 retrieval

说明：

- 当前更多是 contract 保留位
- 不是稳定主路径

## 当前稳定落地

当前真正稳定落地的是：

- `needs_clarification`
- `retrieve_on_raw_query`
