# Relevant Set

## 核心目标

不是强行找唯一 referent，而是先找：

- 和 query 相关的对象
- 和 query 相关的结论
- 和 query 相关的用户陈述
- 和 query 相关的历史上下文入口

## relevant set 的来源

- recent conversation
- active working memory entries
- registry question objects
- memory anchors

## relevant set 的作用

- 给 `binding` 做 rewrite / resolution
- 给 `challenge` 找被质疑对象
- 给 answer side 做引用恢复
- 给 retrieval 决定当前 query 的补全方向

## 筛选原则

第一步：

- recent window
- entry type filter
- explicit pattern filter
- confidence / status filter

第二步：

- 产出小 relevant set
- 交给主大模型做最终 resolution

