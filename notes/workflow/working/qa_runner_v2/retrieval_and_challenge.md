# Retrieval And Challenge

## 正式分层

- `retrieval_quality`
  - 检索层粗 gate
  - 回答：
    - 结果值不值得继续往后传
    - 是否要 repair
    - 是否命中太弱

- `evidence_check`
  - challenge / review 任务层 adjudication
  - 回答：
    - 当前证据是否足以支撑当前目标
    - 是否仍需要更多证据

## 什么时候检索

默认应检索：

- 法规 / 案例 / 文档事实型问题
- challenge / review
- compare / multi-query
- 命中 memory 摘要但摘要不足

可不检索：

- 纯改写 / 翻译 / 润色
- 纯会话型复述
- 当前窗口内就能完成且不依赖外部证据的问题

## 本轮收口：Retrieval Gate 轻策略化

`retrieval_gate_worker` 当前不再只是“要么检索、要么不检索”的粗 gate，
而是稳定区分几类轻策略原因：

- `knowledge_scope_unclear`
- `scope_info_turn`
- `parallel_queries`
- `challenge_turn`
- `knowledge_query`
- `memory_hit_needs_hydrate`
- `context_answer_ok`

当前结论固定为：

- `follow_up` 仍不进入 `handling_mode`
- `follow_up`
  - 通过 `use_context / need_context_binding / binding_result`
  - 间接影响 retrieval gate
- memory 命中但摘要不足时：
  - 优先走 `memory_hit_needs_hydrate`
  - `use_memory_first = true`
  - 是否继续检索，再由 knowledge / challenge / policy flags 决定

## 本轮收口：QA Route 中的 Memory Anchor Hydration

当前 `qa route` 已接入最小可消费的 `memory anchor -> hydrate`：

- 只在：
  - 已命中 `memory_anchors`
  - `memory_anchor_summary_sufficient = false`
  - 且当前 turn 需要上下文 / challenge / answer-side support
  时触发

- hydrate 输出当前只进入：
  - `recent_messages`
  - binding candidate side

- 当前明确不做：
  - 把 hydrate 结果直接伪装成最终 evidence
  - 重做 memory planner
  - 改写 memory owner 边界

因此当前更准确的说法是：

- memory anchor
  - 负责历史锚定
- hydrate
  - 负责把可追溯上下文补回 QA route 的可消费层
- existing evidence / retrieval
  - 仍然分别由 challenge / retrieval 链负责

## Challenge 的正式角色

challenge 负责：

1. target resolution orchestration
2. evidence adjudication orchestration
3. answer constraints orchestration

challenge 内部允许补检索，但只能作为受控 follow-up retrieval。

## 本轮收口：Challenge 重构边界

### 1. challenge 仍属于 `qa route`

- `challenge` 当前不是独立 route。
- 它是 `qa route` 内部的一条任务分支：
  - 由 `handling_mode = challenge` 打开
  - 由 `enabled_powers` 中的 `challenge_power` 执行

更准确地说：

- `qa route`
  - 是单轮问答执行主线
- `challenge`
  - 是 `qa route` 内部的“争议点复审”模式

### 2. `qa route` 当前定位

`qa route` 现在的定位不是“纯 retrieval route”，也不是“纯 chat route”，而是：

- 面向单轮答复的轻量执行主线
- 可按需挂接：
  - `context binding`
  - `retrieval`
  - `challenge/review`
- 最终产出：
  - `ExecutionPayload`
  - 再交给主回答模型

它更像：

- `single-turn answer execution route`

而不是：

- 长链编排 route
- 多阶段 planner route

### 3. Challenge 现在怎么进入主链

当前 `qa route` 内部链路可以压成：

- `context binding (if enabled)`
- `retrieval gate`
- `retrieval (if needed)`
- `retrieval_quality`
- `challenge/review (if enabled)`
- `payload -> answer`

其中 challenge 进入后不是自己另起一套 target 语义，而是优先消费：

- `binding_result.bound_targets`
- `binding_result.resolved_target_ids`
- `binding_result.relevant_set`

如果没有稳定 target：

- 不继续做 challenge adjudication
- 直接返回 `needs_clarification`

所以这轮 challenge 重构的关键变化是：

- challenge 不再把自己当“重新理解 query 的模块”
- challenge 更明确地变成：
  - target-aware evidence review layer

### 4. Challenge 当前真正负责什么

challenge 当前负责：

1. 吃 `context binding` 结果，确定质疑对象
2. 用现有 `evidence_candidates` 先做 existing-evidence 判断
3. 不够时触发受控 `follow-up retrieval`
4. 产出：
  - `review status`
  - `review findings`
  - `answer constraints`

### 5. Challenge 当前不负责什么

challenge 当前不负责：

- 重新做完整的 intent routing
- 重新做独立的 context binding 主判断
- 在没有 binding contract 时自己再做一轮 target rebinding
- 深吃 retrieval repair 的全部诊断细节
- 用模型做细粒度 evidence adjudication

### 6. 当前 adjudication 的定位

当前 challenge 的证据裁决主要由 `ReviewWorker` 完成：

- `retrieval_quality_check`
  - 检索层粗质量检查
- `evidence_check`
  - target/evidence coverage 判断
- `re_evaluate`
  - 把证据判断翻译成：
    - `success`
    - `partial_success`
    - `needs_clarification`
    - `insufficient_evidence`

因此这一轮之后，challenge 的工作边界更清楚地变成：

- `ChallengePower`
  - orchestration
- `ReviewWorker`
  - adjudication

### 7. 当前已经稳定投影到下游的 challenge signals

当前在 `qa route` 主链里已经形成稳定 contract 的 challenge / evidence signals 包括：

- `binding_contract_used`
- `binding_fallback_type`
- `binding_reason`
- `used_existing_evidence`
- `retrieve_if_needed.needed`
- `retrieve_if_needed.reason`
- `matched_target_count`
- `review status`
- `answer_constraints`

这些信号当前已经足以支撑：

- challenge 是否继续执行
- 是否需要 follow-up retrieval
- answer side 是否必须保守、是否必须承认不确定性

### 8. 当前阶段的设计取舍

当前阶段仍然保留 coarse-grained adjudication，原因是：

- 先判断“证据整体够不够”已经足以支撑主链
- 暂时不深挖：
  - repair 原因
  - source quality 细分
  - overlap 低还是 coverage 低
  - 细粒度 claim-level adjudication

如果后面继续增强，优先顺序也应是：

1. 先保证 target 质量
2. 再做 challenge evidence coverage
3. 最后才是 fine-grained claim adjudication

## 本轮收口：workflow 内部 `Literal` 类型约束

这轮不改变对外 contract，只收 workflow 内部类型：

- `WorkflowRoute = Literal["qa", "orchestrated", "chat", "reject"]`
- `WorkflowHandlingMode = Literal["normal", "challenge", "clarify", "scope_info", "unsupported"]`

当前结论固定为：

- 对外 `route / handling_mode` 仍然按 string 读写
- 内部 workflow 主链不再完全裸 `str`
- `follow_up` 仍然不属于 `handling_mode`
- `follow_up`
  - 属于 intent/context/binding 维度
  - 通过 `use_context / need_context_binding / query_style` 生效
- `challenge`
  - 继续属于 `qa route` 内部分支
  - 不因为这轮类型收口改变职责边界

## 本轮收口：Challenge Evidence Coverage 增强

这轮不把 `ChallengePower` 做成更重的裁判模块，而是继续保持：

- `ChallengePower`
  - orchestration
- `ReviewWorker`
  - coarse evidence adjudication

### 1. 这轮增强的重点

增强点只放在 evidence coverage：

- 更稳地复用 existing evidence
- 更稳地决定何时需要 follow-up retrieval
- 更稳地围绕缺口 target 做 targeted retrieval

这轮不做：

- fine-grained claim adjudication 进入主链
- challenge 深吃 retrieval repair 全诊断
- challenge 内新增重 LLM adjudication 步骤

### 2. existing evidence 复用的当前口径

`ReviewWorker.evidence_check(...)` 现在仍以 coarse gate 为主，但口径更明确了：

- 先看 target / evidence refs overlap
- 如果 target 没有可用 refs，可允许有限文本对齐加分
- 如果只有文本相关、但没有 grounding，则视为：
  - `related_only`
  - 仍然需要 follow-up retrieval

所以当前已有 evidence 会被区分成三类：

- 已足够支撑
- 只是相关，不足以支撑
- 完全没覆盖

### 3. follow-up retrieval 当前如何更 target-aware

当前 follow-up retrieval 继续沿用：

- `query + target refs + target text -> support query units`

但这轮进一步固定了两条边界：

- 只围绕 `needs_more_evidence_targets` 补检索
- multi-target challenge 时，按缺口 target 分开构 support unit，再统一 merge

这意味着：

- 不会因为任意 challenge 默认补检索
- 不会把已覆盖 target 也重新一起搜一遍

### 4. 当前仍然不进入主链的后续增强

如果后面继续增强，下一步只能从这两个入口切入：

1. challenge evidence coverage
2. fine-grained claim adjudication

其中：

- coverage 仍然优先
- fine-grained adjudication 仍应作为后续独立小步骤或 helper，而不是并入 `ChallengePower`
