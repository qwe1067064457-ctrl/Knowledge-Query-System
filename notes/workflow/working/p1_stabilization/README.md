# Workflow P1 Stabilization README

这个目录用于承接 **workflow 收口后的 P1 优化与稳定化** goal。

它和 `working/refinement/` 的关系是：

- `refinement/`
  - 保留上一个阶段的完整工作痕迹
  - 不再继续作为当前活跃 goal 的状态写入目录
- `p1_stabilization/`
  - 承接当前 P1 goal 的活跃状态、压缩交接、阶段性判断

## 目录职责

这个目录关注：

- workflow 主链剩余的 P1 级 owner-first / accessor / `summary_view()` 不一致点
- 兼容层 dict fallback 与 typed owner 的边界澄清
- 当前 goal 的推进状态与压缩续接

不负责：

- 重做 workflow typed contract 主线
- 扩展到 graph.agent / memory / session / context
- 覆盖或替换 `refinement/` 的阶段记录

## 文件说明

### `todo.md`

记录当前 P1 goal 的：

- 当前轮次
- 当前 focus
- next focus
- 最近完成项

### `compression_handoff.md`

记录当前 P1 goal 压缩前后的结构化交接信息。

重点保留：

- 当前 P1 收口进度
- 最近验证状态
- 下一步 focus
- 当前识别到的 P1 / P2 边界

### `decisions.md`

记录当前 P1 goal 新产生的阶段性决策。

如果某条结论已经明显稳定到值得长期引用，应该优先提炼到：

- `docs/adr/`

### `known_issues.md`

记录当前 P1 阶段已确认的剩余风险、兼容层陷阱和不建议扩展的路径。

## 使用规则

1. 当前 goal 的活跃状态只写到这个目录，不回写到 `refinement/`
2. `docs/adr/` 继续作为稳定正式层共用
3. 如果某轮只是推进当前 goal，优先更新：
   - `todo.md`
   - `compression_handoff.md`
4. 如果某轮产出新的长期稳定规则，再考虑提炼到 `docs/adr/`
