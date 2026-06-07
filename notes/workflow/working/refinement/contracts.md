# Workflow Contracts

> 注：与 `QA Runner V2` 直接相关的最新 contract，特别是 `retrieval gate / retrieval_quality / evidence_check / session working memory / memory anchor`，已迁移到 `notes/workflow/working/qa_runner_v2/contracts.md`。本页主要保留 workflow v1 完善期与通用 contract 口径。

## Purpose

这份文档只记录当前 workflow 主线已经确认的 contract 口径。

它关注：

- typed owner 是谁
- 对外 dict contract 还保留什么
- 当前高频消费入口是什么

## Core Payload Contract

当前核心中间表示是：

- `ExecutionPayload`

职责：

- 聚合 workflow 产物
- 承载 typed bundle 或兼容 dict bundle
- 向外导出稳定 dict contract
- 提供 summary view 访问入口

当前高频入口：

- `context_bundle_obj()`
- `plan_bundle_obj()`
- `review_bundle_obj()`
- `context_summary_view()`
- `plan_summary_view()`
- `review_summary_view()`
- `evidence_summary_view()`

## Session State Contract

- `SessionDialogueState`
  - owner: `context.models.SessionDialogueState`
  - persistence owner: `context.session.session_manager.SessionManager`

字段语义：

- `focus_question_object_id`
  - 当前短程 follow-up 最值得继续承接的 `question_object`
- `focus_question_object_text`
  - 与 `focus_question_object_id` 对应的文本快照
- `focus_predicate`
  - 当前仍在延续的属性/谓词
- `recent_question_objects`
  - 最近仍值得作为 bound query 候选的问题对象快照
- `recent_evidence_topics`
  - 最近证据主题摘要
- `resolution_confidence`
  - 当前 state 自身稳定度，限定为 `high|medium|low`
- `last_update_reason`
  - 最近一次 state 更新原因

边界：

- `state` 是 session-scoped runtime state
- `state` 不等于 `registry`
- `state` 不等于 `daily_log`
- `state` 不承担长期记忆角色

## Bound Query Prompt Contract

- `state_update_prompt`
  - 输入：
    - 上一轮 `state`
    - 最近少量对话
    - 候选 `question_object`
    - 候选 evidence topics
    - 当前用户问题
  - 输出：
    - `focus_question_object_id`
    - `focus_question_object_text`
    - `focus_predicate`
    - `recent_question_objects`
    - `recent_evidence_topics`
    - `resolution_confidence`
    - `last_update_reason`

- `bound_query_rewrite_prompt`
  - 输入：
    - 当前 `state`
    - 最近少量对话
    - 候选 `question_object`
    - 当前用户问题
  - 输出：
    - `resolved_target_ids`
    - `rewritten_query`
    - `confidence`
    - `needs_clarification`

## Policy Ownership Contract

- `workflow.policy.build_workflow_plan(...)`
  - owner for:
    - `route`
    - `handling_mode`
    - `rewrite_query`
    - `enabled_powers`
    - `policy_flags`
    - `knowledge_scope_status`

- `QaRouteRunner`
  - 消费：
    - `enabled_powers`
    - `rewrite_query`
    - `knowledge_scope_status`

- `answer side`
  - 消费：
    - `route`
    - `handling_mode`
    - `cite_sources`
    - `use_planner`
    - `decompose_query`
    - `should_ask_clarification_first`
    - payload key events / review summary / binding summary

- 约束：
  - `policy_flags` 不应在 answer side 无边界散读
  - 强行为 policy 由 runner / prompt projector 集中消费

## Bundle Contracts

### Context

- `ContextBindingResult`
  - 承载 binding 结果
- `ContextBundle`
  - typed owner for context bundle

当前高频消费：

- `binding_obj()`
- `bound_targets()`
- `query_unit_dicts()`
- `summary_view()`

### Plan

- `PlanBundle`
  - typed owner for planning bundle

当前高频消费：

- `summary_view()`
- `step_count()`
- `checkpoint_count()`
- `comparison_unit_count()`
- `bound_target_ref_count()`
- `is_refined()`
- `is_fallback()`

### Review

- `EvidenceAssessmentResult`
  - evidence coverage / follow-up retrieval 状态 owner
- `ReviewEvaluationResult`
  - re-evaluate 结果 owner
- `ReviewBundle`
  - final review contract owner

当前高频消费：

- `summary_obj()`
- `summary_view()`
- `matched_target_ref_list()`
- `unsupported_target_ref_list()`
- `needs_more_evidence_target_list()`
- `unsupported_target_count()`
- `needs_more_evidence_target_count()`
- `evidence_assessment_obj()`
- `summary_view()`
- `matched_target_refs()`
- `unsupported_target_refs()`
- `needs_more_evidence_targets()`
- `target_count()`
- `matched_target_count()`
- `status_summary()`
- `follow_up_retrieval_attempted()`
- `follow_up_retrieval_improved()`
- `follow_up_retrieval_sources()`
- `follow_up_retrieval_retrieved_evidence_count()`

当前 owner-first 口径：

- `summary_view()` 应优先消费 `EvidenceAssessmentResult.summary_view()`
- 高频 accessor 应优先消费 assessment owner，而不是优先信任 fallback summary
- `summary_obj()` / `to_dict()["review_summary"]` 也应优先消费 assessment owner，而不是直接回落到 `_normalized_summary()`

### Evidence

- `EvidenceRefCandidate`
  - challenge/review 可直接消费的 typed evidence candidate owner
- `RetrievalUnitResult`
  - per query unit retrieval result owner
- `EvidenceBundle`
  - final retrieval bundle owner

当前高频消费：

- `query_unit_result_objs()`
- `summary_view()`
- `summary_obj()`
- `query_unit_count()`
- `merged_evidence_count()`
- `source_ref_count()`
- `source_ref_list()`
- `retrieval_quality_status()`
- `repairable_unit_count()`
- `repaired_unit_count()`
- `missing_evidence_flag()`
- `coverage_query_unit_count()`
- `coverage_source_count()`
- `to_evidence_ref_candidate_objs()`
- `to_evidence_ref_candidates()`

## Current External Compatibility

当前对外仍维持：

- stable dict contract outside

也就是说：

- workflow 内部越来越按 typed object 流转
- 对外消费链暂时仍可吃 dict shape

## Current High-Value Ownership Rules

1. summary 不应由 payload 或外层临时拼装
2. bundle 自己拥有自己的 summary contract
3. power 之间的数据交换边，优先走 typed owner 导出接口
4. 允许保留兼容 `get(...)` / `__getitem__`，但新逻辑优先 typed accessor
