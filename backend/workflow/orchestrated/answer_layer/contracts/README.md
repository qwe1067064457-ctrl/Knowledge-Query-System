# answer_layer contracts

## 职责

这里放 answer layer 的纯数据协议。

## 本质作用

这些 contracts 的本质作用，是把 answer-facing 结果和最终 prompt blocks 的结构稳定下来，避免每次都从 transport bundle 临时拼。

## 放什么

- `AnswerAssemblyPackage`
- answer prompt blocks contract

## 不放什么

- 不放 execution graph runtime
- 不放最终模型调用逻辑

## 与相邻层的边界

- 给 `projectors` 和 shared prompt mapping 共同消费
