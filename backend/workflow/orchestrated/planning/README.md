# planning

## 职责

这里负责 `orchestrated` 的 planner owner。

## 本质作用

它更本质地解决的问题，是把复杂请求稳定压成最小可执行图，而不是把一个复杂句子直接塞给执行层自由发挥。

## 放什么

- planner worker
- planning power 入口
- planner prompt

## 不放什么

- 不放 graph runtime
- 不放最终回答映射

## 与相邻层的边界

- 它消费 binding frame、query units、task frame
- 它产 `ExecutionGraph`
- 它不拥有状态机
