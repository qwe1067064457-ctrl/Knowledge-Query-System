# Workflow Decisions

## D-001: Workflow 阶段资料先落在 notes/workflow/working/refinement

- 决策
  - workflow 当前阶段性资料先统一放在 `notes/workflow/working/refinement/`
- 理由
  - 当前 workflow 仍在快速收口
  - 还不适合一开始就提炼成正式 docs/adr
- 影响范围
  - 当前 workflow 的架构、contract、进度、压缩交接都先在该目录维护

## D-002: typed contract inside, stable dict contract outside

- 决策
  - workflow 内部优先推进 typed object orchestration
  - 对外继续维持稳定 dict contract
- 理由
  - 可以逐步收口而不打断现有消费链
- 影响范围
  - `ExecutionPayload`
  - bundles
  - power / runner / worker 的交界

## D-003: ReviewBundle 是 review contract owner

- 决策
  - review summary / review confidence / review scope 的最终 contract ownership 下沉到 `ReviewBundle`
- 理由
  - 避免 `ChallengeResult` 或外层逻辑重复拼 review summary
- 影响范围
  - `ChallengeResult`
  - `ReviewBundle`
  - `challenge_power`
  - review 消费链

## D-004: 当前不把 workflow 继续扩到 legacy memory/session/context 接线

- 决策
  - 当前轮次只继续补 workflow 主链，不推进 legacy `memory / session / context / 主 agent` 接线
- 理由
  - 用户已明确当前阶段不做这条线
- 影响范围
  - 当前 todo 与压缩交接都不纳入这些模块
