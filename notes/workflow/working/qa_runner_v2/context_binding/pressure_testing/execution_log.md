# Context Binding 压测执行记录

## 说明

这份文档用于记录每轮 `Context Binding` 压测的实际执行情况。

建议记录：

- 压测时间
- 使用的样本批次
- 命中的 `query_style`
- relevant set 大小
- `matched_by`
- `fallback_type`
- 是否进入 challenge / retrieval
- 主要异常

## 当前状态

已开始第一轮最小样本压测。

## Round 1

- 时间：2026-05-26
- 范围：`sample_set.md` 第一轮最小闭环
- 覆盖：
  - follow-up 正例
  - follow-up 歧义例
  - challenge 正例
  - challenge 歧义例
  - standalone 正例
  - memory-anchor 正例
  - challenge 消费链 1 例

### Case A1 - follow-up 正例

- query：`第二点展开讲讲`
- 输入上下文：
  - `working_memory.answer_unit` x2
  - 无 `recent candidates`
  - 无 `memory anchors`
- 实际结果：
  - `query_style = follow_up`
  - `candidate_pool_size = 1`
  - `relevant_set_size = 1`
  - `matched_by = ordinal_rule`
  - `resolved_target_ids = ["wm_answer_2"]`
  - `rewritten_query = "第二点：一年期劳动合同试用期上限为一个月。 第二点展开讲讲"`
  - `fallback_type = null`
- 判定：
  - 符合预期

### Case A3 - follow-up 歧义例

- query：`这个呢`
- 输入上下文：
  - `working_memory.answer_unit` x2
  - `recent_messages` 指向 `relevant set` 与 `writer`
- 实际结果：
  - `query_style = follow_up`
  - `candidate_pool_size = 2`
  - `relevant_set_size = 2`
  - `matched_by = fallback`
  - `resolved_target_ids = []`
  - `fallback_type = needs_clarification`
  - `fallback_reason = multiple_relevant_targets`
- 判定：
  - 符合预期
  - 当前系统对纯弱显式 query 更倾向保守澄清，而不是伪造目标

### Case B1 - challenge 正例

- query：`你刚才说 challenge 还没完全统一，这个具体指什么`
- 输入上下文：
  - `working_memory.answer_unit` x2
  - `working_memory.review_outcome` x1
  - `recent_messages` x2
- 实际结果：
  - `query_style = follow_up`
  - `candidate_pool_size = 3`
  - `relevant_set_size = 3`
  - `matched_by = llm_resolution`
  - `resolved_target_ids = ["wm_answer_challenge_contract"]`
  - `rewritten_query = "ChallengePower 为什么还没完全统一进 Context Binding V2 contract"`
  - `fallback_type = null`
- 判定：
  - 部分符合预期
  - 目标恢复正确
  - 但 `query_style` 实际落在 `follow_up`，不是样本里原先写的 `challenge`

### Case B3 - challenge 歧义例

- query：`这个说法有问题`
- 输入上下文：
  - `working_memory.user_assertion` x1
  - `working_memory.answer_unit` x2
- 实际结果：
  - `query_style = challenge`
  - `candidate_pool_size = 3`
  - `relevant_set_size = 3`
  - `matched_by = fallback`
  - `resolved_target_ids = []`
  - `fallback_type = needs_clarification`
  - `fallback_reason = multiple_relevant_targets`
- 判定：
  - 符合预期

### Case C1 - standalone 正例（现有实现偏差）

- query：`working memory 和 memory anchor 的区别是什么`
- 输入上下文：
  - 无 `working_memory`
  - 无 `recent candidates`
  - 无 `memory_anchors`
- 实际结果：
  - `query_style = multi_target`
  - `candidate_pool_size = 0`
  - `relevant_set_size = 0`
  - `matched_by = fallback`
  - `resolved_target_ids = []`
  - `fallback_type = needs_clarification`
  - `fallback_reason = no_relevant_targets`
- 判定：
  - 不符合样本原预期
  - 当前 `query_style` 分类器因为命中 `和`，将其判成 `multi_target`
  - 这会阻止 `standalone -> retrieve_on_raw_query` 路径

### Case D1 - memory-anchor 正例

- query：`如果 daily log 命中了之前那段讨论，它怎么参与 relevant pool`
- 输入上下文：
  - `memory_anchor` x1
  - `recent_messages` x1
- 实际结果：
  - `query_style = standalone`
  - `candidate_pool_size = 1`
  - `relevant_set_size = 1`
  - `matched_by = single_relevant_candidate`
  - `resolved_target_ids = ["session_older"]`
  - `fallback_type = null`
- 判定：
  - 基本符合预期
  - 这里实际没有进入 LLM，因为 relevant set 已缩到单个 memory anchor

### Case B1C - challenge 消费链

- query：`你刚才说 challenge 还没完全统一，这个依据是什么？`
- 输入上下文：
  - `binding_result` 来自 B1
  - `candidate_targets.answer_unit` x1
  - `existing evidence` x1
- 实际结果：
  - `binding_contract_used = true`
  - `used_existing_evidence = true`
  - `triggered_additional_retrieval = true`
  - `status = insufficient_evidence`
  - `matched_target_count = 0`
  - `follow_up_retrieval_attempted = true`
  - `follow_up_retrieval_improved = false`
- 判定：
  - 已经对齐到同一 target contract
  - 但这条例子没有复用 existing evidence 直接成功，而是进入了补检索后仍证据不足

## Round 1 小结

- 稳定命中：
  - ordinal follow-up
  - 弱显式歧义澄清
  - memory anchor 进入 relevant pool
- 暴露偏差：
  - `working memory 和 memory anchor 的区别是什么` 当前会误判为 `multi_target`
  - 部分 challenge-like 追问更容易被分类成 `follow_up`
- challenge 消费链现状：
  - 已优先消费 `binding_result`
  - existing evidence-first 方向成立
  - 但具体证据匹配是否足够，仍强依赖 evidence 质量

## Round 2

- 时间：2026-05-26
- 范围：
  - 修复后的自包含对比 query
  - challenge evidence 充分场景
  - challenge evidence 不足场景

### Case C1R - 自包含对比 query 修复验证

- query：`working memory 和 memory anchor 的区别是什么`
- 输入上下文：
  - 无 `working_memory`
  - 无 `recent candidates`
  - 无 `memory_anchors`
- 实际结果：
  - `query_style = standalone`
  - `candidate_pool_size = 0`
  - `relevant_set_size = 0`
  - `matched_by = fallback`
  - `fallback_type = retrieve_on_raw_query`
  - `fallback_reason = query_self_contained`
- 判定：
  - 符合修复后预期
  - 这条 query 不再被误判成 `multi_target`

### Case B4 - challenge evidence 正例

- query：`你刚才说 challenge 还没完全统一，这个依据是什么？`
- 输入上下文：
  - `binding_result` 已给出单个 `answer_unit target`
  - `existing evidence` x1
- 实际结果：
  - `binding_contract_used = true`
  - `used_existing_evidence = true`
  - `triggered_additional_retrieval = false`
  - `status = success`
  - `matched_target_count = 1`
  - `follow_up_retrieval_attempted = false`
- 判定：
  - 符合预期
  - 说明 challenge 已能在 evidence 足够时直接成功，不会无意义补检索

### Case B5 - challenge evidence 反例

- query：`你刚才说 challenge 还没完全统一，这个依据是什么？`
- 输入上下文：
  - `binding_result` 已给出单个 `answer_unit target`
  - `existing evidence` x1，但和 target ref 不对齐
  - `retrieval_power` 可用
- 实际结果：
  - `binding_contract_used = true`
  - `used_existing_evidence = true`
  - `triggered_additional_retrieval = true`
  - `status = insufficient_evidence`
  - `matched_target_count = 0`
  - `follow_up_retrieval_attempted = true`
  - `follow_up_retrieval_improved = false`
- 判定：
  - 符合预期
  - 说明 challenge 已能把“binding target 正确但 evidence coverage 不足”单独暴露出来

## Round 2 小结

- 已确认修复：
  - `working memory 和 memory anchor 的区别是什么` 现在回到 `standalone -> retrieve_on_raw_query`
- 已补齐 challenge evidence 双分支：
  - evidence 足够 -> 直接成功
  - evidence 不足 -> follow-up retrieval，仍不足则 `insufficient_evidence`
- 当前更清楚的边界：
  - target contract 已基本稳定
  - challenge 的主要不确定性更多转移到 evidence coverage，而不是 binding 本身

## Round 3

- 时间：2026-05-26
- 范围：
  - 当前线程近 20 轮真实问法
  - 不新增人工样本，只验证真实样式

### Case R3-1 - 自包含架构问法 1

- query：`是不是使用context binding power才能得到relevant set?`
- 输入上下文：
  - 无 `working_memory`
  - 无 `recent candidates`
  - 无 `memory_anchors`
- 实际结果：
  - `query_style = standalone`
  - `candidate_pool_size = 0`
  - `relevant_set_size = 0`
  - `matched_by = fallback`
  - `fallback_type = retrieve_on_raw_query`
  - `fallback_reason = query_self_contained`
- 判定：
  - 符合预期

### Case R3-2 - 自包含架构问法 2

- query：`ContextBindingPower应该来自于working_memory / recent candidates / memory_anchors? working_memory 来自于原始近对话?`
- 输入上下文：
  - 无 `working_memory`
  - 无 `recent candidates`
  - 无 `memory_anchors`
- 实际结果：
  - `query_style = standalone`
  - `candidate_pool_size = 0`
  - `relevant_set_size = 0`
  - `matched_by = fallback`
  - `fallback_type = retrieve_on_raw_query`
  - `fallback_reason = query_self_contained`
- 判定：
  - 符合预期

### Case R3-3 - 真实线程追问

- query：`这不是意图识别的问题吗?`
- 输入上下文：
  - `working_memory.answer_unit` x2
  - `working_memory.review_outcome` x1
  - `recent_messages` x2
- 实际结果：
  - `query_style = standalone`
  - `candidate_pool_size = 3`
  - `relevant_set_size = 3`
  - `matched_by = llm_resolution`
  - `resolved_target_ids = ["wm_answer_query_style_vs_intent"]`
  - `rewritten_query = "这是不是 binding 层 query-style 分类的问题，而不是顶层 intent 问题？"`
- 判定：
  - target resolution 正确
  - 但内部 `query_style` 仍然偏粗，没有把这种弱显式线程追问识别成 follow-up

### Case R3-4 - 真实线程总结性追问

- query：`所以,不管是哪种场景,我们都需要有一个relevant set,后面是不是要真正的消费这个relevant的set?`
- 输入上下文：
  - 无 `working_memory`
  - 无 `recent candidates`
  - 无 `memory_anchors`
- 实际结果：
  - `query_style = multi_target`
  - `candidate_pool_size = 0`
  - `relevant_set_size = 0`
  - `matched_by = fallback`
  - `fallback_type = needs_clarification`
  - `fallback_reason = no_relevant_targets`
- 判定：
  - 不符合人工语义预期
  - 当前 `都` 仍然会把某些自包含总结问法推向 `multi_target`

## Round 3 小结

- 真实线程里的两条自包含架构问法已经能稳定走 `standalone -> retrieve_on_raw_query`
- 真实线程里的弱显式追问仍然可能在 `query_style` 上被判粗，但大模型能靠 relevant set 兜住
- 当前 `multi_target` 规则仍对 `都` 这类词偏敏感，会误伤部分自包含总结问法

## 当前压测收口状态

- 时间：2026-05-26
- 当前主样本策略：
  - 以当前线程近 20 轮真实对话样式为主
  - 不继续大规模补人工边界样本
  - 只有再次出现明确 blocker 时，才补最小样本
- 当前 workflow 测试结果：
  - `python -m pytest -c backend_test\\workflow\\pytest.ini backend_test\\workflow -q`
  - `99 passed`
- 当前结论：
  - 已完成一轮基于当前线程近 20 轮真实对话样式的 `Context Binding` 压测
  - 已记录 relevant set / resolution / fallback / challenge consumption 的代表性样本结果
  - 当前没有新的 workflow 范围内 blocker
  - 当前保留的仅是可接受粗糙点，见 `findings.md`

## Round 4

- 时间：2026-05-26
- 范围：
  - 使用 `backend/.env` 中的真实 LLM 配置
  - 走 `SessionWorkingMemoryWriter -> ContextBindingPower.bind(...) -> live llm_call`
  - 不再使用 fake/stub LLM

### Case R4-1 - live LLM + working memory follow-up/challenge 混合问法

- query：`为什么说 context binding 这条线还没完全收住？`
- 输入上下文：
  - `SessionWorkingMemoryWriter` 从上一轮 answer_text 中写出：
    - `focus_task`
    - `answer_unit` x3
    - `review_outcome`
  - `recent_messages` x2
  - `llm_call` 使用真实 provider 配置
- 实际结果：
  - `query_style = challenge`
  - `candidate_pool_size = 4`
  - `relevant_set_size = 4`
  - `matched_by = fallback`
  - `fallback_type = needs_clarification`
  - `fallback_reason = llm_resolution_failed`
- 判定：
  - 规则层与 working memory 链路正常
  - 已真正进入 live LLM 路径
  - 但当前环境下未拿到可解析的 LLM resolution 结果

### Case R4-2 - live LLM + working memory challenge 问法

- query：`为什么说 challenge 这条线现在更大的不确定性在 evidence coverage？`
- 输入上下文：
  - `SessionWorkingMemoryWriter` 从上一轮 answer_text 中写出：
    - `focus_task`
    - `answer_unit` x3
    - `review_outcome`
  - `recent_messages` x2
  - `llm_call` 使用真实 provider 配置
- 实际结果：
  - `query_style = challenge`
  - `candidate_pool_size = 4`
  - `relevant_set_size = 4`
  - `matched_by = fallback`
  - `fallback_type = needs_clarification`
  - `fallback_reason = llm_resolution_failed`
- 判定：
  - 规则筛选与 relevant set 构建正常
  - 真实模型调用未产出可被当前 parser/validator 接住的结果

## Round 4 小结

- 已确认：
  - `backend/.env` 已提供真实 LLM 配置
  - `ContextBindingPower` 的 live LLM 路径确实被执行
  - `SessionWorkingMemoryWriter -> ContextBindingPower.bind(...)` 全链路可以跑到 live llm_call
- 当前暴露：
  - 在当前环境中，live LLM 结果没有稳定落成可解析 resolution，而是统一收束到 `llm_resolution_failed -> needs_clarification`
