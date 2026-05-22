# Workflow Contracts

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
