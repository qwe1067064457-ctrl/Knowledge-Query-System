# Workflow P1 Stabilization Decisions

## D-001: 当前 P1 goal 的活跃状态与 refinement 阶段隔离

- 决策
  - 当前 goal 的活跃状态不再回写到 `notes/workflow/working/refinement/`
  - 新建 `notes/workflow/working/p1_stabilization/` 承接本 goal 的阶段性资料
- 理由
  - 避免当前 P1 goal 覆盖上一个阶段的 refinement 工作痕迹
  - 让新 goal 的压缩续接只依赖当前目录
- 影响范围
  - `todo.md`
  - `compression_handoff.md`
  - 当前 goal 的阶段性决策与已知问题

## D-002: 剩余的 summary fallback 主要保留在 types 兼容层，不再继续下沉

- 决策
  - 当前 P1 阶段审计后，剩余的 `summary` / `_normalized_summary()` / dict fallback 主要保留在 `backend/workflow/types.py` 的兼容层
  - 不再为了继续消灭这些 fallback，而扩大到新一轮主线重构
- 理由
  - workflow 主执行路径里的高频状态读取已经基本切到 typed accessor / `summary_view()`
  - 剩余 fallback 主要承担：
    - stable dict contract 兼容
    - owner 缺席时的 summary 回填
    - findings/legacy payload 仍可恢复语义
- 影响范围
  - `ReviewBundle`
  - `PlanBundle`
  - `ContextBundle`
  - `ExecutionPayload` 的对外 dict compatibility
