# Case Schema

- `case_id: str`
- `trace_id: str`
- `source: offline_seed | offline_replay | online_sample`
- `working_memory_summary: object`
- `expected_focus_task_present: bool`
- `expected_resolved_query_present: bool`
- `expected_review_outcome_present: bool`
- `expected_handoff_ready: bool`
- `user_feedback: like | dislike | null`
