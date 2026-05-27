# Workflow README

`notes/workflow/` 是当前 `workflow` 工作线的主题入口。

它负责承接：

- workflow 主链的当前边界
- typed contract / bundle contract 的当前口径
- 完善阶段的当前进度
- 主动压缩前后的结构化交接信息

当前 `workflow` 仍处于完善阶段，所以阶段性材料主要放在：

- `working/refinement/`
- `working/qa_runner_v2/`

其中已经连续多轮稳定、可长期引用的专题，开始独立提炼到：

- `context_binding_v2/`

更抽象、跨专题且长期稳定的结论，仍再继续提炼到：

- `docs/adr/`

也就是说：

- `working/refinement/`
  - 继续承接阶段性细节、压缩交接、当前 goal 推进状态
- `working/qa_runner_v2/`
  - 承接 QA Runner V2 的独立架构、边界、检索链、memory 回锚与续接资料
- `context_binding_v2/`
  - 承接已经收官、可长期引用的 `context binding` 正式专题知识
- `docs/adr/`
  - 只承接已经稳定、适合长期正式引用的 workflow 架构结论

## 推荐阅读顺序

如果你是第一次进入 workflow 主题，建议按下面顺序：

1. `context_binding_v2/README.md`
2. `context_binding_v2/architecture.md`
3. `context_binding_v2/contracts.md`
4. `context_binding_v2/production_readiness.md`
5. `working/qa_runner_v2/README.md`
6. `working/qa_runner_v2/architecture.md`
7. `working/qa_runner_v2/contracts.md`
8. `working/qa_runner_v2/compression_handoff.md`

如果你要看 workflow v1 完善期主线，再读：

9. `working/refinement/architecture.md`
10. `working/refinement/contracts.md`

如果你要了解已经稳定、不希望在后续 goal 中反复重议的结论，再继续读：

11. `../docs/adr/ADR-0001-workflow-layer-boundaries.md`
12. `../docs/adr/ADR-0002-workflow-typed-inside-dict-outside.md`
13. `../docs/adr/ADR-0003-workflow-owner-first-summary-contracts.md`

## 当前目录职责

- `working/`
  - workflow 的阶段性材料与中间态收口资料

## 当前规则

1. workflow 的阶段性信息优先写到 `working/refinement/` 或 `working/qa_runner_v2/`
2. `context binding` 这类已收官专题，优先写到 `context_binding_v2/`
3. 只有更抽象、跨专题且长期稳定的内容，才继续提炼到 `docs/adr/`
4. 不要把 workflow 关键信息只留在聊天记录里
