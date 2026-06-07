# Case Schema

第一阶段 case 的最小字段如下：

- `case_id: str`
- `trace_id: str`
- `source: offline_seed | offline_replay | online_sample`
- `user_query: str`
- `knowledge_evidence_summary: object`
- `retrieval_summary: object`
- `workflow_summary: object`
- `answer_text: str`
- `core_summary_present: bool`
- `user_feedback: like | dislike | null`

## 说明

- `knowledge_evidence_summary` 优先来自 `retrieval_run.output_summary.evidence_summary`
- `workflow_summary` 优先来自 `workflow_run.output_summary`
- 如果 observability 摘要中没有最终回答正文，整理真实 trace case 时必须额外补 `answer_text`
