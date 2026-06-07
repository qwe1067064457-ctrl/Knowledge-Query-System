# execution_layer executors

## 职责

这里放 capability executor registry 和各 capability executor。

## 本质作用

它更本质地解决的问题，是把“unit 的能力类型”映射到稳定的执行入口，而不是让 route 或状态机直接理解每种 capability 的内部细节。

## 放什么

- capability executor
- registry

## 不放什么

- 不放全局状态机
- 不放 prompt render

## 与相邻层的边界

- 给 `execution_layer.engine` 提供 unit 级执行策略
- 只补 unit contract，不拥有全局 execution graph
