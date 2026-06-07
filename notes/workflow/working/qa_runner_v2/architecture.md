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
    - `ChallengePower(仅 challenge mode)`
    - `payload`
  - `orchestrated_runner` 串：
    - `global binding frame`
    - `decomposition(only explicit parallel cases)`
    - `planning -> execution_graph`
    - `execution layer`
    - `retrieval_quality(consumed by execution)`
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
  - `execution_worker` 下新增 executor registry：
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

`need_retrieval gate -> retrieval -> retrieval_quality -> ChallengePower(仅 challenge mode) -> WorkflowPayload -> light answer projection -> shared final render`

## Chat / Reject 轻链路

`chat` 与 `reject` 继续收敛为轻路由，不是缩小版 `orchestrated`。

- `chat`
  - 主链：`route -> optional context binding -> WorkflowPayload -> answer signal filter -> prompt render -> shared final render`
  - 第一版只补 `context binding`
  - 不进入 retrieval / challenge / planner / execution
- `reject`
  - 主链：`route -> route-local reject decision -> WorkflowPayload -> answer signal filter -> prompt render -> shared final render`
  - 只产轻量 `reject_summary / answer_constraints / key_events`
  - 不新增 reject 专属 answer layer

这里的 `answer signal filter` 不是新的 answer layer，只是在 shared final render 之前筛出主回答模型真正需要看到的高层信号。

当前主回答路径继续收口为：

- 默认主路径：`workflow -> answer signal filter -> prompt render -> _astream_model_answer`
- 兼容 fallback：`_astream_agent_answer`
  - 只作为 legacy tool-agent 的显式兼容入口
  - 不再作为 `qa/orchestrated` 的默认主路径
- legacy 知识路径：`knowledge_orchestrator`
  - 继续可执行
  - 但不再作为 workflow 未来默认扩展入口

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

当前 `orchestrated` 的收口方向改为：

`resolver/control signal -> workflow policy admission -> orchestrated route -> global binding frame -> decomposition(显式并列时才开启) -> planning(execution graph) -> execution layer -> ExecutionRuntimeResult -> WorkflowPayload -> orchestrated answer layer -> shared final render`

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
- `ChallengePower`
  - 是 challenge-specific orchestration
  - 只在 `handling_mode=challenge` 时进入
  - 不是 execution 尾部的可选外挂
