# Workflow P1 Stabilization TODO

current_round: 3  
last_completed_round: 3  
current_focus: P1 完成度审计已完成，当前已明确主执行路径剩余 fallback 主要属于兼容层  
next_focus: 如需继续推进，应开下一个更小的 workflow goal，而不是继续在当前 P1 goal 中扩大收口范围

## In Progress

- [ ] 如需继续推进，仅处理新的、更明确的小目标
  - 目标：避免在当前 goal 已基本完成时，为了清空兼容层 fallback 而扩大范围

## Next

- [ ] 若后续再开 workflow goal，优先围绕：
  - 新的 seam
  - 新的 integration
  - 或新的稳定层提炼
  而不是继续机械清理兼容层 fallback

## Done Recently

- [x] 完成当前 P1 goal 的完成度审计：
  - 主执行路径里的高频状态读取已基本切到 typed accessor / `summary_view()`
  - 剩余 summary fallback 主要属于 `types.py` 兼容层
- [x] 明确当前阶段不再为了清空兼容层 fallback 而扩大改动范围
- [x] `EvidenceAssessmentResult` 新增 `has_target_coverage_state()`
- [x] `ReviewBundle.summary_view()` / `target_count()` / `matched_target_count()`
  现在在 owner 已接管 target coverage 时，会优先保留 owner 的显式 `0`
- [x] 新增黑盒测试：owner 显式 `0` 的 target counts 不再被 stale summary 覆盖
- [x] workflow 黑盒回归提升到 `62 passed`
- [x] 新建 `notes/workflow/working/p1_stabilization/`
  - `README.md`
  - `todo.md`
  - `compression_handoff.md`
  - `decisions.md`
  - `known_issues.md`
- [x] 当前 goal 的活跃状态已与 `working/refinement/` 隔离
- [x] `notes/workflow/working/README.md` 已补 `p1_stabilization/` 目录职责
- [x] `PlanBundle.summary_dict()` 改为与 `summary_view()` 共用同一条导出语义
- [x] 新增黑盒测试：`PlanBundle.summary_dict() / summary_obj() / to_dict()['plan_summary']` 一致性
- [x] workflow 黑盒回归提升到 `61 passed`
- [x] 上一个 goal 已完成 workflow typed contract 主线收口
- [x] 上一个 goal 已把稳定结论提炼到 `docs/adr/`
  - `ADR-0001-workflow-layer-boundaries.md`
  - `ADR-0002-workflow-typed-inside-dict-outside.md`
  - `ADR-0003-workflow-owner-first-summary-contracts.md`

## Rules

- 当前 goal 的活跃状态不再继续写入 `notes/workflow/working/refinement/`
- 稳定正式结论继续共用 `docs/adr/`
- P1 阶段优先做小而清晰的 owner-first / fallback / `summary_view()` 对齐
