# Retrieval Rubric

## 范围

这里只评 `Knowledge retrieval` 质量，不评长期记忆检索，不评性能。

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
- `off_topic`
- `insufficient_evidence`
- `evidence_unused`
