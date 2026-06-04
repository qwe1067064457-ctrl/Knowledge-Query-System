# Case Schema

- `case_id: str`
- `trace_id: str`
- `source: offline_seed | offline_replay | online_sample`
- `memory_input_summary: object`
- `persist_summary: object`
- `expected_write: bool`
- `expected_memory_type: str | null`
- `expected_scope: str | null`
- `anchor_before: str`
- `anchor_after: str | null`
- `user_feedback: like | dislike | null`
