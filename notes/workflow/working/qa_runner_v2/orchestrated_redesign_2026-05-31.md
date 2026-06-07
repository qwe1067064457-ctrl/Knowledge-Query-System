# Orchestrated Redesign 2026-05-31

## 这轮要锁死什么

这轮重设计先锁 owner 和主链，不继续加新层。

核心边界：

- `route`
  - 顶层分流和 payload 收口
- `power`
  - 某条流程的编排 owner
- `worker`
  - unit 会复用的最小能力
- `helper`
  - 纯辅助，不承载业务 owner

## 正式主链

### QA route

`route -> ContextBindingPower? -> RetrievalPower? -> ChallengePower(仅 challenge mode) -> WorkflowPayload -> light answer projection -> shared final render -> main answer model`

### Orchestrated route

`route -> binding/planning powers -> LangGraph execution -> ExecutorRegistry -> unit executors -> WorkerRegistry -> ExecutionRuntimeResult -> WorkflowPayload -> orchestrated answer layer -> shared final render -> main answer model`

## Challenge 的位置

`ChallengePower` 不是 execution 尾部外挂。

更准确地说：

- `ChallengePower` 是 challenge-specific orchestration
- 只有 `handling_mode=challenge` 时，route 才进入这条 challenge path
- challenge path 内部会复用：
  - target selection
  - evidence check
  - challenge re-evaluate
  - follow-up retrieval planning
  - support query build

## ReviewWorker 收窄

现在 review 核心只保留：

- `retrieval_quality_check`
- `evidence_check`
- `challenge_re_evaluate`

不再把下面这些默认算成 review 核心：

- finding summary
- answer constraint assembly
- 整体 review outcome packaging

如果这些逻辑只在 `ChallengePower` 内部用一次，就留在 power 内部 helper/assembler，不为了“拆得整齐”硬抽 worker。

## Bundle / Payload 口径

- `ExecutionRuntimeResult`
  - execution runtime 的直接产物
- `ExecutionPayload`
  - route-facing rich structured transport
  - 不是薄压缩
  - 不新增 query/result 中间层
- `ChallengeResultBundle`
  - `ReviewBundle` 的新口径
  - 当前先通过兼容 alias 过渡，不一次性打碎旧 contract

## QA route 不该做什么

QA route 可以保留 route-level summary，例如：

- `payload.status`
- `key_events`
- `binding_summary`
- retrieval events

但 QA route 不应自己产 challenge-specific semantic summary，例如：

- 哪些 target 被支持
- 哪些 target 证据不足
- follow-up retrieval 是否改善 challenge 结论

这些语义仍归 `ChallengePower`。
