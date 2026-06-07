# Retrieval Rubric

## 范围

这里只评 `Knowledge retrieval` 质量，不评长期记忆检索，不评性能。

## 术语

- `aggregation`
  - 含义：把规则层与模型层的维度结果整理成最终维度标签与总分的过程。
- `fallback`
  - 含义：当模型层缺失、报错、超时或返回非法结果时，最终整理层退回使用规则层结果。

## 维度

- `presence`
  - `good`：检到多条可用证据
  - `weak`：检到证据但偏少
  - `bad`：没有可用证据
- `relevance`
  - `good`：证据紧扣当前 query
  - `weak`：部分相关，但有偏题或泛化
  - `bad`：明显偏题
- `sufficiency`
  - `good`：证据足以支撑回答
  - `weak`：有证据，但覆盖不足
  - `bad`：不足以支撑回答
- `usability`
  - `good`：证据明显被 answer path 用上
  - `weak`：可能被用上，但关系不稳
  - `bad`：证据基本没被用上

## 权重

- `presence = 0.20`
- `relevance = 0.35`
- `sufficiency = 0.25`
- `usability = 0.20`

## 原因标签

- `no_evidence`
  - 含义：没有检到可用证据。
  - 触发：`merged_evidence_count = 0` 或明确缺证据。
  - 边界：有证据但不够，不应标成 `no_evidence`，应考虑 `insufficient_evidence`。
- `off_topic`
  - 含义：证据明显偏离当前 query。
  - 触发：relevance 维度为 `bad`。
  - 边界：部分相关但不够全面，不应标成 `off_topic`。
- `insufficient_evidence`
  - 含义：证据相关，但数量或覆盖面不足以支撑回答。
  - 触发：sufficiency 维度为 `bad`。
  - 边界：完全没有证据时，优先标 `no_evidence`。
- `evidence_unused`
  - 含义：证据虽然存在，但最终回答基本没有利用它们。
  - 触发：usability 维度为 `bad`。
  - 边界：回答只是利用得不充分，不应直接标成 `evidence_unused`。
