# ADR-0001: Workflow Layer Boundaries And Execution Responsibilities

## Status

Accepted

## Context

`workflow` 在完善阶段已经连续多轮稳定收口，最核心的稳定结论之一是：

- `control` 不应接管 workflow 内部细节
- `workflow` 内部需要明确分层，避免 runner、power、worker、helper 职责漂移

如果这个边界不被正式记录，后续维护和 agent 续接很容易重新出现下面的问题：

- `control` 重新混入 route-specific 执行细节
- `runner` 同时承担重过程实现
- `helper` 侵占 `worker` 的职责
- 新增逻辑时反复重议“这一层到底该放哪里”

## Decision

确立 `workflow` 的正式边界和内部分层如下：

### 顶层边界

主链保持：

`input -> evidence -> resolved -> control -> workflow -> execution_payload -> final answer`

其中：

- `control`
  - 只输出执行相关语义
  - 当前正式字段：
    - `route`
    - `handling_mode`
    - `capabilities`
    - `trace`
- `workflow`
  - 只负责消费 `control` 结果并组织执行前置链
  - 不回到 understanding / rule-heavy 决策层

### workflow 内部分层

- `policy`
  - 负责 `control -> workflow plan`
  - 不直接做 route-specific 执行
- `dispatcher`
  - 负责 route 到 runner 的分发
- `runner`
  - 负责 route 主干编排
  - 负责启动 power
  - 不承接重过程实现
- `power`
  - 负责一个能力块的流程编排
- `worker`
  - 负责重过程、可复用过程
- `helper`
  - 只做局部修补、轻量整理、局部响应辅助

### 当前阶段的明确范围外

当前 workflow 正式边界不扩展到：

- `context_manager`
- `memory`
- `session`
- 主 agent 与这些模块的正式接线
- legacy `memory_indexer.py`
- legacy `prompt_builder.py`
- legacy `session_manager.py`

## Consequences

### Positive

- 后续新增 workflow 逻辑时，分层落点更清楚
- `control` 与 `workflow` 的边界不需要反复重议
- runner、power、worker、helper 的职责更容易被 agent 和开发者复用
- workflow 主题材料可以把“阶段性细节”和“稳定边界”分开沉淀

### Negative / Tradeoffs

- 某些短期看起来方便的跨层实现会被约束住
- 如果未来要把 `workflow` 与 `session/memory` 正式接线，需要开新决策，而不是直接在现有边界上偷偷扩展

## Revisit Signals

出现下面情况时，可以考虑重开这个 ADR：

- `control` 被证明必须承载更多执行层语义才能稳定工作
- `runner` 与 `power/worker` 的职责分界持续造成高摩擦
- workflow 正式进入与 `session/memory/context` 的集成阶段
