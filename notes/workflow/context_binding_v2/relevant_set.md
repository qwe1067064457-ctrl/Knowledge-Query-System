# Relevant Set

## 核心目标

`relevant set` 的目标不是强行找唯一 referent，而是先找：

- 和 query 相关的对象
- 和 query 相关的结论
- 和 query 相关的用户陈述
- 和 query 相关的历史上下文入口

## relevant pool 的来源

- recent candidates
- active working memory entries
- memory anchors

## relevant set 的作用

- 给 `ContextBindingPower` 做 rewrite / resolution
- 给 `ChallengePower` 定位可能被质疑的对象
- 给 answer side 做引用恢复
- 给 retrieval 提供 query 补全方向

## 筛选链

第一步是规则压缩：

- recent/type/status filter
- explicit pattern filter
- confidence / status filter
- simple score ranking

第二步才是主大模型 resolution。

当前阶段的 relevant set 仍然是规则第一版，不是高鲁棒 retriever。
