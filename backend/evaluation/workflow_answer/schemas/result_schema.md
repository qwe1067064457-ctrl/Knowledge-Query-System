# Result Schema

第一阶段 result 的最小字段如下：

- `case_id`
- `trace_id`
- `source`
- `user_feedback`
- `retrieval.dimension_labels`
- `retrieval.dimension_scores`
- `retrieval.score`
- `retrieval.label`
- `retrieval.reasons`
- `answer.dimension_labels`
- `answer.dimension_scores`
- `answer.score`
- `answer.label`
- `answer.reasons`
- `grader_metadata`
- `needs_human_review`
- `human_review_reasons`
- `review_priority`

## 说明

- `dimension_labels` 保留维度级别的 `good | weak | bad`
- `score` 是综合分
- `reasons` 是 bad case 原因标签
- `grader_metadata.rule_result_meta` 记录规则层结果元信息
- `grader_metadata.model_result_meta` 记录模型层结果元信息
- `grader_metadata.finalize_meta` 记录聚合、回退、hard cap 与最终分的元信息
