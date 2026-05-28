# QA Runner E2E 执行记录

## 说明

这里记录端到端样本的两层结果：

1. `QA Runner payload`
2. 主回答模型输出

建议每条样本记录：

- query
- 上下文包摘要
- payload.status
- binding 摘要
- key_events
- answer_constraints
- 主回答模型输出摘要
- 最终判定

## 当前状态

已建立目录与样本集，待按真实线程样本逐批执行。

第一批建议优先执行：

- E2E-R3
- E2E-R5
- E2E-R6
- E2E-R8

原因：

- 这 4 条都依赖上下文
- 都能观察 `binding -> payload -> answer model`
- 比纯 standalone 更能暴露真实噪音和 fallback 行为

## Round 1

- 时间：2026-05-26
- 范围：
  - 当前线程近 20 轮真实对话样式
  - `QA Runner payload -> answer prompt -> 主回答模型`
- 已执行样本：
  - `E2E-R8`
  - `E2E-R4`
  - `E2E-R6`

### Case E2E-R8 - 下一步策略追问

- query：`那我们现在怎么做? 就是还要去调大模型吗?现在build model里面我们调的是MiniMax了。`
- 输入上下文：
  - `recent_messages` = 3 条
  - `working_memory.answer_unit` = 3 条
  - `working_memory.focus_task/review_outcome` = 若干
  - 无 `registry_entries`
- payload 实际结果：
  - `status = ready`
  - `binding_summary = single_relevant_candidate`
  - `matched_by = single_relevant_candidate`
  - `query_style = standalone`
  - `relevant_set_size = 1`
  - `review_status = not_applicable`
  - `key_events = ("binding_applied",)`
- 主回答模型：
  - 返回非空
  - 但出现明显 `<think>` 前缀
  - 内容方向偏“先追问不稳定具体表现”，而不是直接给下一步建议
- 判定：
  - payload 可接受
  - 主回答模型输出方向可理解，但存在明显 `<think>` 泄露

### Case E2E-R4 - relevant set 总结追问

- query：`所以,不管是哪种场景,我们都需要有一个relevant set,后面是不是要真正的消费这个relevant的set?`
- 输入上下文：
  - `recent_messages` = 3 条
  - `working_memory.answer_unit` = 3 条
  - 无 `registry_entries`
- payload 实际结果：
  - `status = ready`
  - `binding_summary = single_relevant_candidate`
  - `matched_by = single_relevant_candidate`
  - `query_style = multi_target`
  - `relevant_set_size = 1`
  - `review_status = not_applicable`
  - `key_events = ("binding_applied",)`
- 主回答模型：
  - 返回非空
  - 同样出现 `<think>` 前缀
  - 说明主回答模型能接住 payload，但当前输出形式不干净
- 判定：
  - payload 没有塌
  - `query_style` 仍偏粗
  - 主回答模型存在推理文本泄露

### Case E2E-R6 - 模型归因质疑

- query：`那是模型的问题, 不是我们prompt问题?`
- 输入上下文：
  - `recent_messages` = 3 条
  - `working_memory.answer_unit` = 3 条
  - `registry_entries.question_object` = 1
  - `registry_entries.evidence_ref` = 1
- payload 实际结果：
  - `status = needs_clarification`
  - `binding_summary = needs_clarification`
  - `matched_by = fallback`
  - `fallback_type = needs_clarification`
  - `query_style = standalone`
  - `relevant_set_size = 2`
  - `review_status = needs_clarification`
  - `key_events = ("binding_ambiguous", "clarification_required")`
- 主回答模型：
  - 返回非空
  - 同样出现 `<think>` 前缀
  - 内容与 payload 对齐，保持了“不能直接单点归因，需要补上下文”的保守姿态
- 判定：
  - `QA Runner` 的澄清信号已经能传到主回答模型
  - 但主回答输出仍有 `<think>` 泄露

## Round 2

- 时间：2026-05-27
- 范围：
  - 真实 challenge case 的 coverage 压测
  - 重点观察：
    - `related_only -> targeted retrieval`
    - existing evidence reuse 是否误判 sufficient
    - follow-up retrieval 是否只围绕 coverage 缺口 target 触发

### Case E2E-C1 - related-only existing evidence 后成功补齐

- query：`那是模型的问题, 不是我们prompt问题?`
- 输入上下文：
  - `recent_messages` = 2 条
  - `registry_entries.question_object` = 1
  - `registry_entries.evidence_ref` = 1（related-only, 无 grounded ref）
  - `retrieval_power` = enabled
- payload 实际结果：
  - `status = ready`
  - `review_status = success`
  - `used_existing_evidence = True`
  - `retrieve_if_needed.reason = not_needed`（recovery 后收敛）
  - `follow_up_retrieval_attempted = True`
  - `follow_up_retrieval_improved = True`
- 关键观察：
  - existing evidence 没有被直接误判 sufficient
  - 补检索只围绕 disputed target 发生
  - follow-up query 中保留了目标 claim 文本，没有把 related-only evidence 的描述一起带进去
- 判定：
  - `related_only -> targeted retrieval -> success` 这条链当前是成立的

### Case E2E-C2 - related-only existing evidence 且不提供 recovery

- query：`那是模型的问题, 不是我们prompt问题?`
- 输入上下文：
  - 与 `E2E-C1` 相同 target 与 existing evidence
  - `retrieval_power` = disabled
- payload 实际结果：
  - `review_status = insufficient_evidence`
  - `retrieve_if_needed.needed = True`
  - `retrieve_if_needed.reason = related_evidence_not_grounded`
  - `follow_up_retrieval_attempted = False`
- 关键观察：
  - 只有文本相关的 existing evidence 不会被算作 grounded support
  - 没有 recovery 时，会稳定停在 `insufficient_evidence`
- 判定：
  - 当前 existing evidence reuse 边界比之前更稳，没有“相关即足够”的误判
