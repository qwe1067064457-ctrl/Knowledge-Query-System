# QA Runner V2 Architecture

## 主边界

QA Runner V2 继续采用：

- `route`
- `power`
- `worker`
- `helper`

不保留 `capabilities/` 作为长期 owner。

## 分层职责

- `routes/`
  - 只做编排
  - `qa_runner` 串：
    - `need_retrieval gate`
    - `retrieval`
    - `retrieval_quality`
    - `challenge/review`
    - `payload`
  - `orchestrated_runner` 串：
    - `decomposition`
    - `planning`
    - `retrieval`
    - `retrieval_quality`
    - `review`
    - `payload`

- `powers/`
  - 共享业务能力入口
  - 当前关键 power：
    - `context_binding_power`
    - `retrieval_power`
    - `challenge_power`
    - `planning_power`
    - `decomposition_power`

- `workers/`
  - 重逻辑、可复用逻辑
  - 当前关键 worker：
    - `binding_worker`
    - `review_worker`
    - `planner_worker`
    - `retrieval_gate_worker`
    - `memory_anchor_worker`

- `helpers/`
  - prompt / response / repair / format 类轻辅助

## QA 主链

当前 QA Runner V2 正式主链：

`need_retrieval gate -> retrieval -> retrieval_quality -> challenge/review -> payload -> answer`

约束：

- `context binding`
  - 只作为 bound query / rewrite 辅助层
  - 不再被定义为 QA 主链中心
- `retrieval`
  - 是 QA 正常主链阶段
  - 不再只是 challenge fallback
- `challenge`
  - 允许 follow-up retrieval
  - 但只能作为受控补检索，不替代主 retrieval
