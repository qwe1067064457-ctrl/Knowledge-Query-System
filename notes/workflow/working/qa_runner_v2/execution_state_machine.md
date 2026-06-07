# Orchestrated Execution State Machine

## 当前 owner

当前 `orchestrated` 的 execution 状态机 owner 在：

- `backend/workflow/workers/execution_worker.py`

它不是 planner owner，也不是 route owner。

约束：

- `planner`
  - 只给 `ExecutionGraph` 和 unit contract
- `execution_worker`
  - 才负责状态推进
- capability executor
  - 只补 unit 内部执行策略
  - 不拥有全局状态机

## 当前状态

第一版状态固定为：

- `pending`
- `completed`
- `skipped`
- `degraded`
- `blocked`

## 当前关键转移

### 1. 依赖不满足

- 条件：
  - upstream dependency 不在 `completed/degraded`
  - 或 `proceed_if=all_dependencies_completed` 但上游不是全部 `completed`
- 结果：
  - 当前 unit -> `skipped`
  - `skipped_reason=dependency_not_completed`

### 2. binding clarification

- 条件：
  - `ContextBindingPower` 返回 `needs_clarification`
- 结果：
  - 当前 unit -> `blocked`
  - `skipped_reason=binding_needs_clarification`
  - downstream 继续由 dependency 规则控制

### 3. retrieval quality bad

- 条件：
  - `review_worker.retrieval_quality_check(...)` 返回 `bad`
- 结果：
  - 当前 unit -> `degraded`
  - `skipped_reason=retrieval_quality_bad`

### 4. 正常完成

- 条件：
  - 无 dependency 阻断
  - 无 binding clarification
  - retrieval 若开启且质量非 `bad`
- 结果：
  - 当前 unit -> `completed`

## 当前与 LangGraph 的关系

当前实现不是 LangGraph runtime。

但已经具备 LangGraph-compatible 的三个前提：

- `ExecutionGraph`
- DAG
- 显式 unit state

所以后续如果迁到 LangGraph，推荐迁移顺序是：

1. 先稳定 `GlobalBindingFrame` 和 `ExecutionGraph` contract
2. 再稳定 capability executor contract
3. 最后把当前 `execution_worker` 的状态推进映射到 LangGraph node/state runtime

不要反过来先换 runtime，再回头猜 graph 和 state owner。
