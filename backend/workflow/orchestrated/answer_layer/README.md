# answer_layer

## 职责

这里负责把 rich execution result / `ExecutionPayload` 重组为 answer-facing 结果。

## 本质作用

它更本质地解决的问题，是降噪、保关键语义、重组顺序，让主回答模型不必重新理解 execution graph 和 workflow transport 语义。

## 放什么

- answer-facing contracts
- execution result 到 answer package 的 projectors
- answer layer 自己的 prompts / 规则说明

## 不放什么

- 不放 graph 执行逻辑
- 不放最终 shared system prompt render
- 不放 workflow transport 总包

## 与相邻层的边界

- 上游消费 `ExecutionPayload`
- 下游交给 shared prompt mapping 渲染成文本 prompt blocks
