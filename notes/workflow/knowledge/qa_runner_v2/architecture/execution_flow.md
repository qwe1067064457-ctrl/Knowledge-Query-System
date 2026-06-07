# Execution Flow

## QA 主执行链

当前 `qa route` 的正式主链可以压成：

`context binding -> retrieval gate -> retrieval -> retrieval_quality -> challenge/review -> payload -> answer`

这条主链的核心含义不是“每轮都跑完所有阶段”，而是：

- 先根据 policy 和 context 决定是否启用某些阶段
- 再把阶段产物逐步投影到最终 `ExecutionPayload`
- 最后交给主回答模型做受控自然语言生成

## 分阶段说明

### 1. Context Binding

在 `need_context_binding = true` 时启用。

主要职责：

- 从候选对象中构造 `relevant_set`
- 在需要时解析目标对象
- 返回：
  - `bound_targets`
  - `resolved_target_ids`
  - `relevant_set`
  - `rewritten_query`
  - `fallback_type`

### 2. Retrieval Gate

不是简单的“要不要检索”，而是轻策略 gate。

当前稳定 reason 至少包括：

- `knowledge_query`
- `challenge_turn`
- `memory_hit_needs_hydrate`
- `context_answer_ok`
- `scope_info_turn`
- `knowledge_scope_unclear`

### 3. Retrieval

当 gate 判定需要检索时启用。

主要职责：

- 接受 `QueryUnit`
- 执行 retrieval
- 返回 `EvidenceBundle`

### 4. Retrieval Quality

由 `ReviewWorker.retrieval_quality_check(...)` 承担。

主要职责：

- 判断当前检索结果是否偏弱
- 是否需要 repair
- 是否存在 missing evidence

### 5. Challenge / Review

只在 `handling_mode = challenge` 且 `challenge_power` 启用时进入。

主链为：

`consume binding result -> identify targets -> existing evidence check -> follow-up retrieval(if needed) -> review re-evaluate -> answer constraints`

### 6. Payload

各阶段产物最终落到：

- `ExecutionPayload`
- `ContextBundle`
- `PlanBundle`
- `ReviewBundle`
- `answer_constraints`
- `key_events`

### 7. Answer

主回答模型不负责重新决定执行流。

它消费：

- system prompt
- runtime override
- workflow instructions
- `ExecutionPayload` 投影出的行为与结果约束
- 当前 history messages

当前设计是：

- process-first
- answer-last

## Chat 与 Orchestrated 的对照

### Chat

- 不走完整 QA 主链
- 更像轻响应流

### Orchestrated

- 在 `qa` 的受控答复基础上增加：
  - planning
  - decomposition
  - staged execution organization

因此：

- `qa` = 受控单轮答复
- `orchestrated` = 多步执行编排后答复
