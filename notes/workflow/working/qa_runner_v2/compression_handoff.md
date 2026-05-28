# QA Runner V2 Compression Handoff

当前主线已经确认：

- 代码边界使用 `route / power / worker / helper`
- `capabilities/` 不再视为长期 owner
- QA 正式主链：
  - `need_retrieval gate -> retrieval -> retrieval_quality -> challenge/review -> payload -> answer`
- `qa route` 当前定位：
  - 单轮答复执行主线
  - 可按需挂接 `context binding / retrieval / challenge`
- `challenge` 当前定位：
  - 属于 `qa route` 内部的争议点复审分支
  - 不再自己重做一套 target 语义
  - 优先消费 `context binding` 结果
  - 没有稳定 target 时直接 `needs_clarification`
  - 不再在 challenge 内部自行做 target rebinding
- `challenge/review` 当前稳定 contract：
  - `binding_contract_used`
  - `binding_fallback_type`
  - `binding_reason`
  - `used_existing_evidence`
  - `retrieve_if_needed.needed`
  - `review status`
  - `answer_constraints`
- `challenge evidence coverage`
  - 当前已增强 existing evidence reuse 判断
  - follow-up retrieval 只围绕 coverage 缺口 target 发生
  - `related_only` evidence 仍视为不足，不直接当作 grounded support
- `retrieval_gate_worker`
  - 当前已从纯规则 gate 收成可解释的轻策略 gate
  - 稳定 reason 至少包括：
    - `knowledge_query`
    - `challenge_turn`
    - `memory_hit_needs_hydrate`
    - `context_answer_ok`
    - `scope_info_turn`
    - `knowledge_scope_unclear`
- `memory anchor -> hydrate`
  - 当前已在 `qa route` 接入最小可消费入口
  - 仅在：
    - 命中 `memory_anchors`
    - 摘要不足
    - 且当前 turn 需要外部上下文 / challenge / answer-side support
    时触发
  - hydrate 输出进入：
    - `recent_messages`
    - binding candidate side
  - 不直接伪装成最终 evidence
- `ReviewWorker` 当前角色：
  - 同时服务 `qa` 与 `orchestrated`
  - 在 `qa route` 内承担 coarse evidence adjudication
- `workflow` 内部类型：
  - `route / handling_mode` 已使用 `Literal` 收紧
  - 对外仍保持 string contract
  - `follow_up` 仍不进入 `handling_mode`
  - `follow_up` 继续留在 intent/context binding 维度
- `session working memory`
  - 只保执行连续性
  - 不参与 bound query 主判断
- memory 命中不应只返回摘要
  - `qa route` 当前已支持最小 `anchor -> hydrate`
  - 后续只继续增强命中率与观测，不重做 memory owner

当前仍然明确不做：

- challenge 深吃 retrieval repair 诊断细节
- fine-grained claim adjudication 进入主链

如果后续继续增强，优先级固定为：

1. evidence coverage
2. existing evidence reuse quality
3. fine-grained claim adjudication

继续工作前优先看：

1. `architecture.md`
2. `contracts.md`
3. `retrieval_and_challenge.md`
4. `memory_anchor_and_hydration.md`
5. `todo.md`
