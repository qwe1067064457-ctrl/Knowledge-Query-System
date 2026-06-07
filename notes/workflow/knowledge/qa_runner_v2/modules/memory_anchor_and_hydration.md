# Memory Anchor And Hydration

## 定位

当前 `memory anchor -> hydrate` 不是完整 memory 重构，而是 `qa route` 内的最小可消费接入点。

当前角色分工固定为：

- memory anchor
  - 负责历史锚定
- hydrate
  - 负责把可追溯历史上下文补回 QA route 可消费层
- working memory
  - 负责执行连续性

## 当前最小链路

当前最小链路是：

1. 命中 `memory_anchors`
2. 判断摘要是否已足够
3. 如果摘要不足，按 anchor 回放 transcript 周边上下文
4. hydrate 结果进入：
   - `recent_messages`
   - binding candidate side

## 触发条件

当前最小接入点只在以下条件成立时触发：

- 已命中 `memory_anchors`
- `memory_anchor_summary_sufficient = false`
- 且当前 turn 需要：
  - 外部上下文
  - challenge support
  - answer-side support

## 当前明确边界

当前明确保留的边界：

- hydrate 结果不是最终 evidence
- hydrate 结果只用于补上下文，不直接替代 retrieval
- working memory 不接管历史锚定 owner
- memory anchor 不接管执行连续性 owner

## 与 Retrieval Gate 的关系

当前 `retrieval_gate_worker` 已能显式给出：

- `memory_hit_needs_hydrate`

这说明：

- memory hit 后不是立刻就回答
- 也不是立刻就大检索
- 而是先判断是否需要 hydrate 再决定后续路径

## 当前观测口径

当前至少应观测：

- `memory_anchor_count`
- `hydrated_memory_entry_count`
- `memory_hydrated`
- retrieval gate 是否给出 `memory_hit_needs_hydrate`

## 当前阶段目标

当前阶段不是继续扩 memory owner，而是继续回答这几个问题：

1. hydrate 触发是否过多
2. hydrate 后是否真的减少误 retrieval
3. hydrate 后是否仍然需要 challenge follow-up retrieval
