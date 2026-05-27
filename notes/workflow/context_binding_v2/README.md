# Context Binding V2

这个目录承接 `Context Binding V2` 的正式专题知识。

这里记录的是已经收官、可长期引用的边界，不再把它当作 `working` 中间态。

核心结论：

- `context binding` 是按需触发的 `query rewrite / context resolution` 链
- 它的目标不是唯一恢复 referent，而是先得到可执行的 `relevant set`
- `Session Working Memory` 是 short-term semantic candidate pool
- `memory anchor` 是 long-term memory hit 后的上下文锚点
- 当前版本可内部联调 / 灰度验证，不建议直接生产放量

推荐阅读顺序：

1. `architecture.md`
2. `contracts.md`
3. `relevant_set.md`
4. `working_memory_boundary.md`
5. `challenge_boundary.md`
6. `rulebook.md`
7. `fallbacks.md`
8. `production_readiness.md`
