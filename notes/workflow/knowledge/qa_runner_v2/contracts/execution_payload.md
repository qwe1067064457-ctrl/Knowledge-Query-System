# Execution Payload

## 定位

`ExecutionPayload` 是 `workflow` 主链交给主回答模型之前的统一结果容器。

它的目标不是保存所有内部细节，而是稳定承载：

- 当前 route / handling mode
- 当前执行状态
- 当前 instructions
- context / plan / review 摘要
- answer-side 需要遵守的约束

## 当前稳定字段

当前应视为稳定 contract 的核心字段包括：

- `route`
- `handling_mode`
- `action`
- `status`
- `enabled_powers`
- `instructions`
- `knowledge_scope_status`
- `context_bundle`
- `plan_bundle`
- `review_bundle`
- `answer_constraints`
- `notes`
- `key_events`

## String Contract

对外 contract 当前仍保持 string shape：

- `route` 输出 string
- `handling_mode` 输出 string

内部虽然已使用 `Literal` 收紧类型，但：

- 不引入 `Enum`
- 不改变 `to_dict()` / `from_dict()` 的外部数据形状

## Context Bundle

`context_bundle` 当前承载：

- `trace`
- `binding`
- `binding_summary`
- `candidate_count`
- `query_units`
- `memory_anchor_count`
- `hydrated_memory_entry_count`
- `memory_hydrated`

当前 answer-side 重点消费的是 `summary_view` 投影，而不是要求主模型自己读完整内部对象。

## Review Bundle

`review_bundle` 当前承载：

- `status`
- `review_summary`
- `review_findings`
- `answer_constraints`
- `evidence_assessment`

当前 `challenge / review` 相关稳定 summary signals 包括：

- `binding_contract_used`
- `binding_fallback_type`
- `binding_reason`
- `used_existing_evidence`
- `retrieve_if_needed_needed`
- `retrieve_if_needed_reason`
- `matched_target_count`
- `review status`
- `answer_constraints`

## Key Events

`key_events` 是 harness / 回放层非常重要的一组执行事件。

当前常见事件包括：

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

## Status

`ExecutionPayload.status` 当前主要包括：

- `ready`
- `needs_clarification`
- `rejected`

含义是：

- `ready`
  - workflow 已准备好进入主回答阶段
- `needs_clarification`
  - workflow 已判断当前不应直接给出完整 substantive answer
- `rejected`
  - 当前请求应拒绝
