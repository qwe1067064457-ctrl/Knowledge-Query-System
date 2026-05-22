# Workflow Compression Handoff

handoff_round: 35  
last_verified_test_status: 60 passed (`python -m pytest -c backend_test\\workflow\\pytest.ini backend_test\\workflow -q`)

## Current State

- 已开始把连续多轮稳定的 workflow 结论提炼到 `docs/adr/`
- 当前已形成 3 条正式 ADR：
  - `ADR-0001-workflow-layer-boundaries.md`
  - `ADR-0002-workflow-typed-inside-dict-outside.md`
  - `ADR-0003-workflow-owner-first-summary-contracts.md`
- workflow 主链已经形成：
  - typed power production
  - typed payload carrying
  - typed runner orchestration
  - stable dict contract outside
- `ChallengeResult` 的非成功分支也已经统一走 typed factory
- `ChallengeResult` 已新增 review bundle / summary view 委托入口
- `EvidenceAssessmentResult / ReviewEvaluationResult` 已补 typed helper
- `challenge_power` 已减少一批 assessment dict 回填
- `review_worker.re_evaluate()` 已开始优先消费 assessment accessor
- `ReviewBundle` 的 follow-up retrieval summary 已更多依赖 assessment accessor
- `EvidenceRefCandidate` 已新增 `as_target_candidate()`
- `challenge_power` 最外层已开始正式接受 typed evidence candidate
- “无 target 时回退到 evidence candidate” 这条路径已开始兼容 typed evidence candidate
- `EvidenceAssessmentResult` 已新增 matched/unsupported/needs-more-evidence target ref list accessor
- `ReviewBundle.from_challenge_result(...)` 已开始优先信任 assessment owner，而不是先从 `review_findings` 倒推 target refs
- `EvidenceAssessmentResult` 已新增 `summary_view()`
- `ReviewBundle.from_challenge_result(...)` 已开始直接消费 assessment summary view 的 target count / follow-up retrieval 状态
- `ReviewBundle.summary_view()` 已开始优先消费 `EvidenceAssessmentResult.summary_view()`
- follow-up retrieval 的布尔状态已修成 owner-first 语义，不再让 fallback summary 把 owner 的 `False` 覆盖掉
- `EvidenceBundle.summary_view()` 已开始直接从 owner 字段生成
- `EvidenceBundle.summary_obj()` 已改为反向委托 `summary_view()`
- retrieval 侧高频 accessor 已开始优先消费 `EvidenceBundle.summary_view()`
- `EvidenceBundle.summary_view()` 现已稳定覆盖 repair / coverage 摘要字段
- `ReviewBundle` 的高频 accessor 已开始优先消费 assessment owner
- `ReviewBundle.summary_obj()` 现已改为 owner-first 导出
- `ReviewBundle.to_dict()` 的 `review_summary` 现已走 `summary_obj()`，外部 stable dict contract 也会优先反映 assessment owner，而不是继续携带过期 fallback 值

## Typed Status Snapshot

当前已经明确 typed owner 的主对象：

- `ContextBindingResult`
- `ContextBundle`
- `PlanBundle`
- `ReviewBundle`
- `EvidenceBundle`
- `EvidenceAssessmentResult`
- `ReviewEvaluationResult`
- `RetrievalUnitResult`
- `ExecutionPayload`

## Current Focus

- 提炼 workflow 已稳定的架构结论到更正式层
- 保持 `working/refinement/` 作为阶段性推进与压缩续接目录
- 明确 `docs/adr/` 只承接已经稳定、适合长期正式引用的 workflow 结论

## Next Focus

- 评估是否还有别的 workflow 结论已经稳定到适合进入 ADR
- 如果没有，再回到下一阶段的 workflow P1 优化 / 稳定化 goal

## Confirmed Boundaries

- `control`
  - 只输出执行相关语义，不接管 workflow 细节
- `workflow_policy`
  - 只做 `control -> workflow plan`
- `runner`
  - 启动 power，编排主链
- `power`
  - 负责能力块流程
- `worker`
  - 干重活、可复用过程
- `helper`
  - 只做局部修补
- `EvidenceAssessmentResult`
  - 应负责 evidence assessment 的 typed 状态修改入口
- `ReviewEvaluationResult`
  - 应负责 reevaluation answer constraint 的 typed 更新入口
- `EvidenceAssessmentResult`
  - 应负责 per-target assessment 的 typed 查询入口
- `EvidenceAssessmentResult`
  - 应负责 follow-up retrieval 摘要字段的 typed 查询入口
- `EvidenceRefCandidate`
  - 应负责 challenge/review 可直接消费的 evidence candidate 导出与 target fallback 桥接
- `EvidenceAssessmentResult`
  - 应负责 matched/unsupported/needs-more-evidence target ref 的 owner 级导出
- `EvidenceAssessmentResult`
  - 应负责 target count / matched count / follow-up retrieval 状态的 owner 级 summary view
- `ReviewBundle.summary_view()`
  - 应优先消费 assessment owner，而不是优先信任内部 summary fallback
- `ReviewBundle` accessor
  - 应尽量与 `summary_view()` 保持同一套 owner-first 语义
- `ReviewBundle.summary_obj()`
  - 应作为 owner-first 的外部 dict 导出层，而不是直接回落到 `_normalized_summary()`
- `EvidenceBundle.summary_view()`
  - 应优先直接从 retrieval owner 字段生成，而不是先从 `to_dict()["evidence_summary"]` 回读
- `EvidenceBundle.summary_obj()`
  - 应作为 `summary_view()` 的兼容导出层，而不是独立 owner

## Known Pitfalls

- 不要再把 workflow 关键状态只留在聊天里
- 不要把当前资料混写到 legacy `memory / session / context` 主题
- 不要新增长链路上的 summary dict 直读，优先 typed accessor
- 不要默认假设 evidence candidate 一定是 dict；新逻辑优先兼容 typed `EvidenceRefCandidate`
- 不要优先从 `review_findings` 倒推 target refs；能从 assessment owner 读时应优先走 assessment accessor
- 不要优先从零散 assessment 字段拼 review 计数和 follow-up 状态；能从 assessment summary view 读时应优先走 summary owner
- 布尔型 owner 状态不能用 `or` 合并；必须保留 owner 的显式 `False`
- 不要让 retrieval owner 的 summary 先落成 dict 再回读；能直接从 owner 字段生成时应优先走 summary view
- retrieval 线的新摘要字段应优先补进 `summary_view()`，再决定是否导出到 `summary_obj()`
- `ReviewBundle` 的 accessor 不应比 `summary_view()` 更依赖 fallback summary dict
- `ReviewBundle` 的外部 `review_summary` 导出不应比 `summary_view()` / accessor 更依赖 fallback summary dict
