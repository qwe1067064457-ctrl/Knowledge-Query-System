# Workflow P1 Stabilization Known Issues

## K-001: 当前 goal 不应回写 refinement 活跃状态

- 现象
  - 如果继续更新 `refinement/todo.md` 或 `refinement/compression_handoff.md`，会把上一个 goal 的阶段记录与当前 P1 goal 混在一起
- 处理方式
  - 当前 goal 的活跃状态只写 `p1_stabilization/`

## K-002: P1 优化不应扩展为新一轮主线重构

- 现象
  - 当前阶段已经不是 typed contract 主线收口，而是 owner-first / fallback / summary/export 的稳定化
- 处理方式
  - 只做小范围、一致性导向的收口
  - 不回到大范围主线重做

## K-003: 剩余的 summary dict fallback 主要属于兼容层，不等于必须继续收的 P1

- 现象
  - `backend/workflow/types.py` 里仍保留部分 `_normalized_summary()` / summary fallback 读法
- 处理方式
  - 如果它们主要服务：
    - stable dict contract
    - owner 缺席时的回填
    - findings/legacy payload 兼容
    则按兼容层接受，不继续为了“清零 fallback”而扩大改动面
