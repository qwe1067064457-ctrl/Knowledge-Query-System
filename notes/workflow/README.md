# Workflow README

`notes/workflow/` 是当前 `workflow` 工作线的主题入口。

它负责承接：

- workflow 主链的当前边界
- typed contract / bundle contract 的当前口径
- 完善阶段的当前进度
- 主动压缩前后的结构化交接信息

当前 `workflow` 仍处于完善阶段，所以主材料先放在：

- `working/refinement/`

但其中已经连续多轮稳定的结论，已开始提炼到：

- `docs/adr/`

也就是说：

- `working/refinement/`
  - 继续承接阶段性细节、压缩交接、当前 goal 推进状态
- `docs/adr/`
  - 只承接已经稳定、适合长期正式引用的 workflow 架构结论

## 推荐阅读顺序

如果你是第一次进入 workflow 主题，建议按下面顺序：

1. `working/refinement/architecture.md`
2. `working/refinement/contracts.md`
3. `working/refinement/todo.md`
4. `working/refinement/compression_handoff.md`
5. `working/refinement/known_issues.md`

如果你要了解已经稳定、不希望在后续 goal 中反复重议的结论，再继续读：

6. `../docs/adr/ADR-0001-workflow-layer-boundaries.md`
7. `../docs/adr/ADR-0002-workflow-typed-inside-dict-outside.md`
8. `../docs/adr/ADR-0003-workflow-owner-first-summary-contracts.md`

## 当前目录职责

- `working/`
  - workflow 的阶段性材料与中间态收口资料

## 当前规则

1. workflow 的阶段性信息优先写到 `working/refinement/`
2. 只有明显稳定、需要长期正式引用的内容，才提炼到 `docs/adr/`
3. 不要把 workflow 关键信息只留在聊天记录里
