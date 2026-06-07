# planning prompts

## 职责

这里放 `orchestrated.planning` 层专属 prompt。

## 本质作用

这些文档的本质作用，是把 planner 对 unit 粒度、graph 结构、依赖与条件的口径外显出来，让模型化 planner 可控。

## 放什么

- execution graph planner prompt

## 不放什么

- 不放 binding frame prompt
- 不放最终主回答 prompt

## 与相邻层的边界

- 给 `PlanningPromptHelper` 提供模板
- 不直接推进 execution state
