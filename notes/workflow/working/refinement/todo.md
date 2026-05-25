# Workflow Refinement TODO

current_round: 37  
last_completed_round: 36  
current_focus: 收口 QA Runner 第二版的 session state schema、prompt contract 与 policy ownership  
next_focus: 跑 workflow/session 回归，确认 state/prompt/policy 合约已被测试和文档一起钉住

## In Progress

- [ ] 建立 bound query 黑盒评估样本与统计输出
  - 目标：有一组短程 follow-up 样本，可统计自动绑定成功率、澄清率、误绑率
  - 完成标准：workflow 测试中存在稳定评估样本，且可输出精度统计结果
- [ ] 收口 answer side 对 ExecutionPayload 的高价值消费
  - 目标：让 answer side 优先消费 binding/review/key events 等强信号，减少 planning 等低价值噪音
  - 完成标准：workflow prompt projector 的 QA 消费面不再默认注入低价值流程字段
- [ ] 收口 session state schema、prompt contract 与 policy ownership
  - 目标：state 的字段语义、来源、持久化边界，prompt 的输入输出 contract，policy 的 owner 与消费边界都明确且可测试
  - 完成标准：README / notes 与黑盒测试能共同证明这些边界

## Next

- [ ] 跑 workflow/session 回归，确认 bound query 评估与 payload 收口没有打坏第二版主链
- [ ] 如果 precision 基线稳定，再考虑是否补线下样本扩充和更显式的 payload 事件消费测试
- [ ] 如果 state/prompt/policy 合约稳定，再评估是否需要把其中一部分提炼到更正式层

## Done Recently

- [x] `SessionDialogueState` 新增归一化 contract：
  - 去重 recent question objects / evidence topics
  - 限制 confidence 到 `high|medium|low`
  - `focus_question_object_id` 与 recent objects 保持一致
- [x] `BoundQueryPromptHelper` 新增显式 contract 校验：
  - `validate_state_update_payload(...)`
  - `validate_rewrite_payload(...)`
- [x] `ContextBindingPower` 已开始消费 prompt helper 的显式 contract 校验结果
- [x] 新增黑盒测试：
  - `test_bound_query_prompt_contracts.py`
  - session state persistence normalization 反例
- [x] `context/session/README.md`、`prompts/workflow/README.md`、`notes/workflow/working/refinement/{architecture,contracts}.md`
  已补：
  - state owner
  - prompt 输入输出 contract
  - policy ownership / consumption boundary

- [x] QA Runner 第二版主链已接通：
  - `state + rule + llm resolution/rewrite`
  - coarse review metrics
  - key events in payload
- [x] `registry` 已收成跨轮对象锚点层，只保留：
  - `question_object`
  - `evidence_ref`

- [x] 新增正式 ADR：
  - `ADR-0001-workflow-layer-boundaries.md`
  - `ADR-0002-workflow-typed-inside-dict-outside.md`
  - `ADR-0003-workflow-owner-first-summary-contracts.md`
- [x] `notes/workflow/README.md` 已开始明确区分：
  - `working/refinement/`
  - `docs/adr/`
  的职责边界
- [x] `notes/workflow/working/refinement/README.md` 已补“与正式层的边界”说明
- [x] `ReviewBundle.summary_obj()` 改为 owner-first 导出：
  - `target_count`
  - `matched_target_count`
  - `matched_target_refs`
  - `unsupported_target_refs`
  - `needs_more_evidence_targets`
  - `follow_up_retrieval_*`
  现在会优先消费 assessment owner，而不是直接回落到 `_normalized_summary()`
- [x] `ReviewBundle.to_dict()` 的 `review_summary` 改为走 `summary_obj()`，外部 stable dict contract 不再优先携带过期 fallback 值
- [x] 新增黑盒测试：`ReviewBundle.summary_obj()/to_dict()` 在 owner 与 fallback summary 冲突时，会优先导出 assessment owner 值
- [x] workflow 黑盒回归提升到 `60 passed`
- [x] `ReviewBundle` 的高频 accessor 开始优先消费 assessment owner，而不是先回退到 `_normalized_summary()`
- [x] 新增黑盒测试：`ReviewBundle` accessor 会优先信任 assessment owner 的 target refs / counts / follow-up 状态
- [x] workflow 黑盒回归提升到 `58 passed`
- [x] `EvidenceBundle.summary_view()` 直接暴露：
  - `repairable_units`
  - `repaired_units`
  - `coverage_query_units`
  - `coverage_sources`
- [x] `EvidenceBundle.summary_obj()` / 高频 accessor 继续统一到 `summary_view()` 上
- [x] retrieval 线进一步减少“owner fields -> dict -> 再回读”的链路
- [x] `EvidenceBundle.summary_view()` 开始直接从 owner 字段生成，不再先经由 `to_dict()["evidence_summary"]`
- [x] `EvidenceBundle.summary_obj()` 改为反向委托 `summary_view()`
- [x] `retrieval_quality_status / repairable_unit_count / repaired_unit_count / missing_evidence_flag / coverage_*`
  开始优先消费 `EvidenceBundle.summary_view()`
- [x] 新增黑盒测试：`EvidenceBundle.summary_view()` 现在稳定暴露
  - `repairable_units`
  - `repaired_units`
  - `coverage_query_units`
  - `coverage_sources`
- [x] `ReviewBundle.summary_view()` 开始优先消费 `EvidenceAssessmentResult.summary_view()`
- [x] 修正 follow-up retrieval 布尔状态的 owner-first 语义：
  - owner 提供 `False` 时，不再被 summary fallback 错误覆盖成 `True`
- [x] 新增黑盒测试：`ReviewBundle.summary_view()` 会优先信任 assessment owner 的 target counts 与 follow-up 状态
- [x] `EvidenceAssessmentResult` 新增：
  - `unsupported_target_count()`
  - `needs_more_evidence_target_count()`
  - `summary_view()`
- [x] `ReviewBundle.from_challenge_result(...)` 开始直接消费 assessment summary view 的 target count / follow-up retrieval 状态
- [x] 新增黑盒测试：assessment summary view 可独立驱动 review bundle 的 target count 与 follow-up retrieval 状态
- [x] `EvidenceAssessmentResult` 新增：
  - `matched_target_ref_list()`
  - `unsupported_target_ref_list()`
  - `needs_more_evidence_target_list()`
- [x] `ReviewBundle.from_challenge_result(...)` 开始优先消费 assessment target ref accessor，而不是先从 `review_findings` 倒推
- [x] 新增黑盒测试：即使 `review_findings` 为空，assessment owner 仍能稳定驱动 review summary target refs
- [x] `EvidenceRefCandidate` 新增 `as_target_candidate()`
- [x] `challenge_power` 最外层开始正式接受 typed `EvidenceRefCandidate`
- [x] `challenge_power` 在“无 target 时回退到 evidence candidate”路径上开始兼容 typed evidence candidate
- [x] 新增黑盒测试：typed evidence candidate 可直接驱动 challenge 成功路径
- [x] 新增 `EvidenceRefCandidate`
- [x] `EvidenceBundle` 新增 `to_evidence_ref_candidate_objs()`
- [x] `challenge_power` 的 follow-up retrieval 分支开始直接消费 typed evidence candidate
- [x] `review_worker` 开始兼容 typed evidence candidate / dict candidate 双输入
- [x] `EvidenceAssessmentResult` 新增：
  - `follow_up_retrieval_source_refs()`
  - `follow_up_retrieval_retrieved_evidence_count()`
- [x] `ReviewBundle.from_challenge_result(...)` 的 follow-up retrieval summary 改为优先消费 assessment accessor
- [x] `EvidenceAssessmentResult` 新增：
  - `per_target_assessment_map()`
  - `target_is_matched(...)`
  - `matched_evidence_refs_for(...)`
- [x] `review_worker.re_evaluate()` 开始优先消费 `EvidenceAssessmentResult` accessor
- [x] `EvidenceAssessmentResult` 新增 typed helper：
  - `supporting_evidence_ref_list()`
  - `with_fallback(...)`
  - `with_follow_up_retrieval(...)`
- [x] `ReviewEvaluationResult` 新增 `with_answer_constraints(...)`
- [x] `challenge_power` 去掉一批 assessment dict 回填，改走 typed helper
- [x] `review_worker.re_evaluate()` typed 化为 `ReviewEvaluationResult`
- [x] `ChallengeResult.from_review_evaluation(...)` 接入主链
- [x] `ChallengeResult` 新增 review bundle / summary view 委托入口
- [x] `challenge_power` 的 clarify / fallback / insufficient-evidence 分支统一走 typed factory

## Rules

- 每完成一轮真正的 workflow 收口，都更新轮次与 current/next focus
- 不把 legacy `memory / session / context` 相关事项混到这里
