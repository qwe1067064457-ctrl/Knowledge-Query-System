# Workflow Compression Handoff

> 注：`QA Runner V2` 的后续续接入口已切到 `notes/workflow/working/qa_runner_v2/compression_handoff.md`。本页不再作为 V2 主续接文档。

handoff_round: 37  
last_verified_test_status: workflow 79 passed; session 19 passed

## Current State

- QA Runner 第二版主链已形成：
  - `registry(question_object/evidence_ref)`
  - `session-scoped state`
  - `ContextBindingPower = state + rule + llm resolution/rewrite + clarification gate`
  - `ReviewWorker` coarse review
  - `ExecutionPayload` key events + answer constraints
- 本轮 focus 正在收三件事：
  - `SessionDialogueState` schema 与持久化边界
  - `state_update_prompt` / `bound_query_rewrite_prompt` 的输入输出 contract
  - `policy.py -> QA Runner / answer side` 的 owner 与消费边界
- `workflow_prompt_projector` 已开始从 QA 视角优先消费：
  - `binding_summary`
  - `review_summary`
  - `follow_up_retrieval_*`
  - `insufficient_evidence`
  - `knowledge_scope_status`
  并减少默认 planning 噪音注入

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

- 收口 `SessionDialogueState` 的 schema、来源、更新规则、持久化边界
- 固定 `state_update_prompt` / `bound_query_rewrite_prompt` 的输入输出 contract
- 让 `policy ownership` 在代码和 notes 中都更明确

## Next Focus

- 跑 workflow/session 全量回归，确认本轮 contract 收口没有打坏第二版主链
- 如果 contract 继续稳定，再评估哪些结论适合提炼到更正式层

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
