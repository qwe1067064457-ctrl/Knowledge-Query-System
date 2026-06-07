# Workflow Answer Alignment README

这个目录用于承接 **workflow 与 answer side 的消费链对齐** goal。

它和其他目录的关系是：

- `refinement/`
  - 保留 workflow typed contract 主线收口阶段的记录
- `p1_stabilization/`
  - 保留 workflow 内部 P1 稳定化阶段的记录
- `answer_alignment/`
  - 承接当前 goal：workflow 输出如何被 answer side / graph 消费

## 目录职责

这个目录关注：

- answer side 是否优先消费 typed accessor / `summary_view()`
- workflow -> answer side 这条链上的 ownership 是否清楚
- `backend/graph` 对 workflow summary 的读取是否仍在手工翻旧 dict

不负责：

- 重做 workflow typed contract 主线
- 扩展到 session / memory / context 集成
- 回写前两个 goal 的活跃状态

## 文件说明

### `todo.md`

记录当前 goal 的：

- 当前轮次
- 当前 focus
- next focus
- 最近完成项

### `compression_handoff.md`

记录当前 goal 压缩前后的结构化交接信息。

### `decisions.md`

记录当前 goal 新形成的阶段性决策。

### `known_issues.md`

记录当前 goal 已确认的消费链问题、兼容层边界和不建议扩展的路径。

## 使用规则

1. 当前 goal 的活跃状态只写到这个目录
2. `docs/adr/` 继续作为稳定 workflow 结论的共用正式层
3. 如需继续推进 answer side，对齐工作优先更新：
   - `todo.md`
   - `compression_handoff.md`
