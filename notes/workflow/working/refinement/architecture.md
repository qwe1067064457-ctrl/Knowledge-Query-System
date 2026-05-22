# Workflow Architecture

## Purpose

这份文档只记录当前 `workflow` 的边界、分层和 ownership。

它不记录：

- 完整调试历史
- 每一轮尝试过程
- 与当前 workflow 主线无关的 legacy 模块细节

## Current Boundary

当前主链是：

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

## Workflow Internal Layers

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

## Current Route / Mode Contract

- `route`
  - `qa`
  - `orchestrated`
  - `chat`
  - `reject`

- `handling_mode`
  - `normal`
  - `clarify`
  - `challenge`
  - `scope_info`
  - `unsupported`

约束：

- `handling_mode` 保持单值竞争
- `power` 允许多值组合

## Current Powers

- `retrieval_power`
- `context_binding_power`
- `planning_power`
- `challenge_power`
- `decomposition_power`

其中：

- `decomposition_power`
  - 当前只负责 `parallel_queries`
- `planning_power`
  - 负责更复杂的 plan 组织
- `challenge_power`
  - 负责 challenge / review / follow-up retrieval 这条执行链

## Current Typed Ownership

当前 typed contract 已明确下沉到这些对象：

- `ContextBindingResult`
- `ContextBundle`
- `PlanBundle`
- `ReviewBundle`
- `EvidenceBundle`
- `EvidenceAssessmentResult`
- `ReviewEvaluationResult`
- `RetrievalUnitResult`
- `ExecutionPayload`

当前 ownership 约定：

- summary 属于 bundle 自己
- `ExecutionPayload` 只做 bundle 聚合和转发
- `ReviewBundle` 是 review contract owner
- `EvidenceBundle` 是 retrieval 结果与 evidence 导出 owner

## Out Of Scope For Current Phase

当前阶段明确不处理：

- `context_manager`
- `memory`
- `session`
- 主 agent 与这些模块的正式接线
- legacy `memory_indexer.py`
- legacy `prompt_builder.py`
- legacy `session_manager.py`

这些路径如果有可复用内容，后续按“拔出”处理，但不放入当前 workflow 主线范围。
