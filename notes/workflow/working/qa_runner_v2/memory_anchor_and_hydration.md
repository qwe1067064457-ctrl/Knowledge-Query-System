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
