# Orchestrated Answer Layer

## 它做什么

`orchestrated answer layer` 负责：

- 从 `ExecutionPayload` / rich execution result 中抽取关键信息
- 生成 answer-facing package
- 组织主回答模型需要消费的 prompt blocks
- 消费 capability 级 `result_payload`，避免只保留 unit state
- 把 findings 区分成 `primary / supporting / status`，而不是只给主模型一坨平铺信息

## 它更本质地解决什么问题

它的本质作用不是做“二次薄摘要”，而是做：

- 低损失重组
- 去 transport 噪音
- 保主结论和关键状态
- 保 capability 产出的关键语义 finding
- 让主回答模型不必重建 execution 语义

也就是说，它解决的是“执行结果很多、很工程化，但主回答模型最终应该看什么”的问题。

## 当前 owner 结构

- `backend/workflow/orchestrated/answer_layer/contracts/`
- `backend/workflow/orchestrated/answer_layer/projectors/`
- `backend/workflow/orchestrated/answer_layer/prompts/`

## 与相邻层的边界

- 上游：
  - `execution_layer` / `ExecutionPayload`
- 下游：
  - shared prompt mapping
  - main answer model

它不负责：

- graph 执行
- 最终 shared system prompt render
