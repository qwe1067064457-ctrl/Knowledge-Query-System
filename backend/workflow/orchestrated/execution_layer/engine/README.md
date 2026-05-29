# execution_layer engine

## 职责

这里放 execution layer 的 graph runtime 和状态机。

## 本质作用

它更本质地解决的问题，是让 unit 生命周期和依赖推进变成显式的运行时规则，而不是隐藏在 route 或 executor 里的分支 if/else。

## 放什么

- execution layer runtime
- state machine

## 不放什么

- 不放 capability 内部策略
- 不放 answer-facing projection

## 与相邻层的边界

- 它消费 executor registry
- 它产 rich execution result
