# Orchestrated V2 V1 Notes

## 当前定位

`orchestrated` 现在不再被视为“把多个 power 顺序串起来”的轻 route，而是：

- 一个多步执行编排 route
- 顶层仍受 `workflow policy` admission control 约束
- 内部由 `planner -> execution graph -> execution layer` 驱动

它的目标不是替代 `qa`，而是承接：

- 显式并列 query
- staged query
- conditional branch
- synthesis 型汇总任务

简单 compare / simple verify / 无 execution graph 必要的请求，应优先回落 `qa`。

## 四层边界

推荐继续采用：

`resolver -> control signal -> workflow policy -> route/planning/execution`

其中：

- `resolver`
  - 负责理解收敛
- `control signal`
  - 负责给 workflow 提供稳定的结构化信号
- `workflow policy`
  - 负责 admission control 与能力开关
- `route/planning/execution`
  - 负责具体执行结构化

不要把这几层合并成单一 owner，否则很难区分：

- 理解错了
- admission 配错了
- graph 画错了
- executor 跑错了

## Global Binding Frame

`workflow policy.need_context_binding`

现在应理解为：

- `binding enable flag`
- 只表示后续允许启用 binding 能力

它不表示：

- 已经做了 context binding
- 已经做了 global binding
- 已经 resolved target

新增的 `GlobalBindingFrame` 只负责 frame / hint，当前最小输出：

- `query_is_context_dependent`
- `binding_scope_hint`
- `shared_target_candidates`
- `recommended_binding_mode`
- `segment_hints`
- `notes`

说明：

- `global binding frame` 可以由 cheap rules 触发
- 规则负责 trigger / cheap evidence
- 有 `global_binding_llm_call` 时，允许模型补最终 frame
- prompt owner 当前落在：
  - `backend/prompts/workflow/global_binding_frame_prompt.md`
- 但不应该越权做 deep resolution
- `shared binding` 不是新模块，只是 frame 的一种输出状态
- 单句和多句都允许输出 `segment_hints`
- `segment_hints` 只描述局部上下文依赖分布，不等于 execution unit
- `partial` 应优先收敛到 `selective_per_unit`
- 没有稳定 shared target 时，不应强推 `global_only`

## Contracts Owner

图与执行合同已经开始从大 `types.py` 中拆出，当前应优先看：

- `workflow/contracts/graph.py`

这里集中承接：

- `BindingMode`
- `ExecutionUnitCapability`
- `ExecutionEdgeType`
- `UnitState`
- `GlobalBindingFrame`
- `ExecutionUnit`
- `ExecutionEdge`
- `ExecutionGraph`
- `UnitResult`

当前 `workflow.types` 仍保留 re-export，以兼容旧调用点。

## Planner 与 Execution

`planner` 的 owner 边界：

- 输入 candidate branches 或复杂请求
- 产出 `ExecutionGraph`
- 控制 unit 粒度
- 负责 unit 合并
- 当前支持：
  - 规则 fallback graph builder
  - `planning_llm_call` 驱动的模型化 graph 生成

planner 的模型入口当前约定：

- `recent_messages_summary`
- `working_memory_hints`
- `memory_anchor_hints`
- `global_binding_frame`
- prompt owner 当前落在：
  - `backend/prompts/workflow/execution_graph_planner_prompt.md`

planner prompt 当前应显式约束：

- 优先最小可执行 graph
- 不要把 unit 拆得过碎
- staged / conditional 优先表达依赖，不要伪装成并列 graph
- 多个 branch 共用 retrieval / binding / answer slot 时优先合并
- graph 必须保持 DAG，unit / edge 字段必须满足 schema

`execution layer` 的 owner 边界：

- 按 DAG 跑 unit
- 区分 `parallel / staged / conditional / synthesis`
- 在 unit 执行前按 `binding_mode` 触发 `ContextBindingPower`
- 消费 `retrieval_quality`
- 产出 `UnitResult`

`ExecutionWorker` 之下新增：

- `CapabilityExecutorRegistry`

它负责按 `unit.capability` 分发到：

- `qa_like_executor`
- `chat_like_executor`
- `reject_like_executor`
- `compare_executor`
- `verify_executor`
- `synthesis_executor`

当前约束：

- capability executor 只调用底层 `power / worker / helper`
- 不回调顶层 route runner

当前推荐 binding 策略：

- 默认 `lazy binding`
- 仅在 `global_only + 单一强 shared target` 时做 `pre_shared`

## 当前主链

V1 主链建议固定为：

`resolver/control signal -> workflow policy -> route dispatch -> global binding frame -> decomposition(if explicit parallel) -> planning(execution graph) -> execution layer -> challenge/review(optional) -> payload`
