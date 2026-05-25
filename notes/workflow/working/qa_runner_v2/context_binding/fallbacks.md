# Context Binding Fallbacks

## 原则

找不到对象时，不能只返回“没找到”。

必须返回结构化 fallback。

## fallback 类型

### 1. `needs_clarification`

适用：

- relevant set 里有多个强候选
- 无法高置信唯一解析

输出：

- reason
- candidate target ids
- clarification question

### 2. `rewrite_without_target`

适用：

- 找不到明确 target
- 但 topic 可以恢复

输出：

- reason
- rewritten query

### 3. `retrieve_on_raw_query`

适用：

- query 自包含
- 不需要 binding 也可直接检索

输出：

- reason
- raw query

### 4. `answer_from_context_only`

适用：

- 当前上下文已足够回答
- 不需要 retrieval

输出：

- reason

