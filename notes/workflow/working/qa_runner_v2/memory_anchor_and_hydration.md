# Memory Anchor And Hydration

## 目标

`daily_log / domain_case` 命中后，不只返回摘要文本。

应支持：

1. memory hit
2. 生成历史上下文 anchor
3. 在 challenge 或高需求场景下 hydrate 周边上下文

## 当前最小链路

- `memory_anchor.py`
  - 负责把 `MemoryEntry` 变成可回锚对象
- `memory_anchor_worker.py`
  - 负责 anchor 选择与统一入口
- `context_hydrator.py`
  - 负责按 session transcript 回放周边上下文

## 当前边界

- 这条链服务：
  - challenge
  - 需要历史上下文的长程续接
- 不服务：
  - 普通短句复述
  - 无 anchor 时的上下文伪造

## 本轮实现

当前 `qa route` 已接入最小可消费 hydration 入口：

1. 命中 `memory_anchors`
2. 判断摘要是否已足够
3. 如果摘要不足，再按 anchor 回放 transcript 上下文
4. hydrate 结果进入：
   - `recent_messages`
   - binding candidate side

当前明确保留的边界：

- hydrate 结果不是最终 evidence
- hydrate 结果只用于补上下文，不直接替代 retrieval
- working memory 仍负责执行连续性
- memory anchor 仍负责历史锚定

## 当前观测口径

当前至少会观测：

- `memory_anchor_count`
- `hydrated_memory_entry_count`
- `memory_hydrated`
- retrieval gate 是否给出 `memory_hit_needs_hydrate`

因此下一步重点不再是“有没有 hydrate 入口”，而是：

1. hydrate 触发是否过多
2. hydrate 后是否真的减少误 retrieval
3. hydrate 后是否仍然需要 challenge follow-up retrieval
