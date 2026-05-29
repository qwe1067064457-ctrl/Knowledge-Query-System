# execution_layer

## 职责

这里负责 `orchestrated` 的 graph 执行、状态流转、unit result 收口。

## 本质作用

它更本质地解决的问题，不是直接写给用户一段答案，而是把多步编排任务生产成可被后续层稳定消费的中间执行结果。

## 放什么

- graph runtime / 状态机
- capability executor 分发
- execution result contracts

## 不放什么

- 不放最终回答 prompt
- 不放 workflow transport 总包
- 不放 route 顶层串接

## 与相邻层的边界

- 上游消费 `planning` 产出的 `ExecutionGraph`
- 下游把 rich execution result 交给 `ExecutionPayload` / `answer_layer`
