# Harness Event Model

## 定位

`QA Runner` 当前已经具备较强的 harness 雏形。

这里的 harness 不是单纯的日志堆积，而是：

- 可审计
- 可评估
- 可监督
- 可控

也就是：

- 能回看一次回答经历了什么流程
- 能对各阶段单独打分
- 能把 workflow 约束投影给 answer side
- 能显式控制 fallback / clarification / retrieval

## 当前一级执行事件

建议把以下事件视为一级 harness events：

- `binding_applied`
- `binding_ambiguous`
- `retrieval_performed`
- `retrieval_repaired`
- `retrieval_quality_weak`
- `memory_anchor_hydrated`
- `follow_up_retrieval_attempted`
- `follow_up_retrieval_improved`
- `clarification_required`
- `insufficient_evidence`

## 当前一级状态字段

建议重点观测：

- `route`
- `handling_mode`
- `knowledge_scope_status`
- `binding_summary`
- `binding_fallback_type`
- `matched_target_count`
- `retrieve_if_needed_needed`
- `retrieve_if_needed_reason`
- `review status`
- `memory_hydrated`
- `payload.status`

## 当前一级评估指标

建议优先做这些统计：

- binding hit rate
- binding fallback rate
- retrieval trigger rate
- retrieval weak rate
- follow-up retrieval attempted rate
- follow-up retrieval improved rate
- clarification rate
- insufficient evidence rate
- live timeout rate
- live fallback rate

## 当前设计为什么适合做 harness

当前 `QA Runner` 不是“直接把原 query 丢给主模型”。

它已经具备：

- route-level execution flow
- power / worker phase separation
- explicit intermediate artifacts
- payload-level answer constraints
- replayable key events

因此它非常适合：

- 真实样本评测
- 过程监控
- SFT 标签沉淀
- fallback 行为分析

## 与主回答模型的关系

当前设计不是让 workflow 直接替代 answer model。

而是：

- workflow 负责决定怎么答、答前准备什么、哪些风险要约束
- 主回答模型负责在这些受控约束下做自然语言生成

因此当前模式可以压成：

- process-first
- answer-last

## 当前最主要的运行面 seam

当前 harness 视角下最主要的 seam 已不再是本地主链结构，而是：

- live answer model latency
- live answer model timeout
- provider / runtime availability

这类 seam 更适合走：

- 观测
- 限时保护
- 小步优化

而不是再回头大改 `qa route` 主骨架
