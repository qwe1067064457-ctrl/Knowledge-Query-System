# binding

## 职责

这里负责 `orchestrated` 专属的 global binding framing。

## 本质作用

它更本质地解决的问题，不是替代 deep binding，而是把“是否依赖上下文、依赖范围有多大、后续 binding 应该如何启用”前移成一个独立 owner。

## 放什么

- global binding frame worker
- binding framing 相关 prompt

## 不放什么

- 不放 deep binding engine
- 不放 execution graph
- 不放最终回答映射

## 与相邻层的边界

- 它给 `planning` 和 `execution_layer` 提供 frame / hint
- 它不直接解析最终 target 真相
