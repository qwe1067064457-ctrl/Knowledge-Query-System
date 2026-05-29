# execution_layer helpers

## 职责

这里放 execution layer 的辅助投影和整理逻辑。

## 本质作用

它更本质地解决的问题，是把 engine 产出的 rich execution result 做轻量整理，避免 route 或 answer layer 重复拼状态摘要。

## 放什么

- execution result summary helper

## 不放什么

- 不放 graph runtime
- 不放主回答 prompt 组装

## 与相邻层的边界

- 给 route / answer layer 提供 execution 摘要
