# answer_layer projectors

## 职责

这里放 execution result / `ExecutionPayload` 到 answer-facing package 的投影逻辑。

## 本质作用

它更本质地解决的问题，不是做薄摘要，而是做低损失重组：去掉 transport 噪音，保留主结论、状态和关键约束。

## 放什么

- answer assembly projector
- answer prompt block builder

## 不放什么

- 不放最终模型调用
- 不放 graph 执行逻辑

## 与相邻层的边界

- 上游读 `ExecutionPayload`
- 下游交给 shared prompt mapping
