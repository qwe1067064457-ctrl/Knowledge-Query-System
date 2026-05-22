# Workflow Refinement TODO

current_round: 35  
last_completed_round: 35  
current_focus: ReviewBundle 外部 review_summary 导出 owner-first 收口、workflow typed contract 完成度审计  
next_focus: 扫描 workflow 主链剩余高频 dict 直读，区分 P0 / P1 / P2，判断本阶段是否可验收

## In Progress

- [ ] 继续收 `retrieval -> challenge` 的消费边
  - 目标：更多走 `EvidenceBundle / RetrievalUnitResult / accessor / summary_view`
  - 完成标准：challenge/review 继续减少对 retrieval 明细 dict 的直接读取

- [ ] 继续收 `ChallengeResult / ReviewBundle / review_summary` 的消费链
  - 目标：更多走 `ReviewBundle.summary_view()` 与 object accessor
  - 完成标准：新增逻辑不再优先写 `review_summary[...]`，外部 `review_summary` 导出也不再携带过期 fallback 值

## Next

- [ ] 做一轮 workflow typed contract 完成度审计
  - 目标：扫描 `runners / powers / workers / types`，找还残留的高频 dict 直读
  - 产出：按 `P0 / P1 / P2` 分类剩余点，并判断是否已经接近本阶段验收
- [ ] 评估 `runner` 内部是否还有值得继续下沉到 typed object 的残留桥接

## Done Recently

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
