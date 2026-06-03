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
- `grader_metadata` 记录规则与 LLM grader 的辅助信息，便于复盘
