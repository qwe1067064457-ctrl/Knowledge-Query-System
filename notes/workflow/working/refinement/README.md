# Workflow Refinement README

这个目录承接 `workflow` 在完善阶段的阶段性信息。

它的目标不是替代正式文档，而是为当前开发阶段提供：

- 当前架构边界
- 当前 contract 口径
- 当前 goal 的推进状态
- 压缩前后的结构化交接信息
- 已知坑与设计决策

## 文件职责

### `architecture.md`

记录当前 `workflow` 的架构边界与分层职责。

主要回答：

- `control`、`workflow_policy`、`runner`、`power`、`worker`、`helper` 各自负责什么
- 哪些内容属于 `workflow`
- 哪些内容当前明确不属于 `workflow`

适合写入：

- 边界定义
- ownership 分层
- 主链职责归属

不适合写入：

- 详细调试过程
- 某一轮的临时尝试

### `contracts.md`

记录当前 `workflow` 主链已经确认的 contract 口径。

主要回答：

- typed owner 是谁
- 对外 dict contract 还保留什么
- 当前高频消费入口是什么

适合写入：

- `ExecutionPayload`
- `ContextBundle / PlanBundle / ReviewBundle / EvidenceBundle`
- `EvidenceAssessmentResult / ReviewEvaluationResult / RetrievalUnitResult`
- accessor / `summary_view()` / owner-first 规则

### `todo.md`

记录当前活跃 goal 的推进状态。

主要回答：

- 当前轮次是多少
- 当前 focus 是什么
- 下一步要做什么
- 最近完成了哪些真正的收口项

这个文件应随着新 goal 或新一轮推进持续刷新。

### `decisions.md`

记录关键设计决策及其理由。

主要回答：

- 为什么这样收口
- 为什么不采用另一种方案
- 这个决策影响哪些范围

适合写入：

- 关键分层决策
- contract owner 决策
- 兼容策略决策

### `known_issues.md`

记录当前阶段已经确认的坑、兼容桥接和禁区。

主要回答：

- 哪些地方容易重复踩坑
- 哪些 fallback 逻辑不能乱动
- 哪些 legacy 路径不要继续扩展

适合写入：

- 语义陷阱
- 默认值陷阱
- owner-first 合并陷阱

### `compression_handoff.md`

记录当前对话压缩前后最关键的结构化交接信息。

主要回答：

- 当前主链做到哪一步了
- 最近验证状态是什么
- 下一步接着做什么
- 当前有哪些已确认边界和 pitfalls

它是“继续工作前的快速恢复入口”。

## 使用建议

进入新的 `workflow` goal 前，建议优先阅读：

1. `architecture.md`
2. `contracts.md`
3. `todo.md`
4. `compression_handoff.md`

如果某轮做出了新的稳定结论：

- 更新 `contracts.md` 或 `architecture.md`

如果某轮只是推进当前 goal：

- 优先更新 `todo.md`
- 压缩前重写 `compression_handoff.md`

如果某轮发现新的稳定坑位或新决策：

- 分别更新 `known_issues.md` 或 `decisions.md`

## 当前定位

这里是 `workflow` 的**完善阶段工作目录**。

因此这里的内容默认具有：

- 阶段性
- 可迭代性
- 为续接和压缩服务

只有当某部分结论连续多轮稳定、且需要长期正式引用时，才考虑进一步提炼到更稳定的文档层。

## 与正式层的边界

当前目录负责：

- 阶段性推进状态
- 当前 goal 的 focus / next focus
- 压缩续接
- 还可能继续变化的架构细节与坑位

`docs/adr/` 负责：

- 已经连续多轮稳定的 workflow 架构结论
- 后续 agent / 开发者不应反复重议的长期规则

换句话说：

- 这里回答“现在做到哪、接下来做什么”
- `docs/adr/` 回答“哪些结论已经稳定到值得长期引用”
