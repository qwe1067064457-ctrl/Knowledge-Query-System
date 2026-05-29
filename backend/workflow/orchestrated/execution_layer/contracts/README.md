# execution_layer contracts

## 职责

这里放 execution layer 的纯数据协议。

## 本质作用

这些 contracts 的本质作用，是把 planner、execution、answer layer 之间的接口稳定下来，让 runtime 可以变、层间协议不要乱漂。

## 放什么

- graph 相关 typed contracts
- execution result contracts

## 不放什么

- 不放业务逻辑
- 不放 prompt

## 与相邻层的边界

- 给 `planning`、`execution_layer.engine`、`answer_layer` 共同消费
