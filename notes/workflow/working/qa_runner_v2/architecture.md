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
    - `global binding frame`
    - `decomposition(only explicit parallel cases)`
    - `planning -> execution_graph`
    - `execution layer`
    - `retrieval_quality(consumed by execution)`
    - `challenge/review(optional)`
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
    - `global_binding_worker`
    - `review_worker`
    - `planner_worker`
    - `execution_worker`
    - `retrieval_gate_worker`
    - `memory_anchor_worker`
  - `execution_worker` 下新增 capability executor registry：
    - `qa_like_executor`
    - `chat_like_executor`
    - `reject_like_executor`
    - `compare_executor`
    - `verify_executor`
    - `synthesis_executor`

- `helpers/`
  - prompt / response / repair / format 类轻辅助
  - orchestrated V2 新增：
    - `global_binding_prompt_helper`
    - `planning_prompt_helper`

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

## Orchestrated V2 主链

当前 `orchestrated` 的 V1 收口方向改为：

`resolver/control signal -> workflow policy admission -> orchestrated route -> global binding frame -> decomposition(显式并列时才开启) -> planning(execution graph) -> execution layer -> challenge/review(optional) -> payload -> answer`

约束：

- `workflow policy`
  - 只做 admission control 与能力开关
  - 不做 deep binding
  - 不做 execution graph 构造
- `global binding frame`
  - 只做 frame / hint
  - 输出 `global | partial | none`
  - 不直接产 deep resolution target
- `decomposition`
  - 只处理显式并列 query
  - 不承担隐式 multi-branch 解释
- `planner`
  - 负责把 candidate branches 或复杂请求压成 `ExecutionGraph`
  - 默认要求 DAG
  - 负责 unit 合并，避免 unit 粒度碎片化
  - 允许先走模型化 graph 生成，再回落规则 fallback graph builder
- `execution layer`
  - 才是真正的 orchestrated 执行 owner
  - 区分 `parallel / staged / conditional / synthesis`
  - 按 `pre_shared / lazy / skip` 调用 `ContextBindingPower`
  - 消费 `retrieval_quality` 影响 unit state，而不是只写 `key_events`
