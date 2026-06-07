# Case Schema

- `case_id: str`
- `trace_id: str`
- `source: offline_seed | offline_replay | online_sample`
- `pre_compaction_summary: object`
- `post_compaction_summary: object`
- `pre_compaction_extraction_summary: object`
- `expected_anchor_required: bool`
- `user_feedback: like | dislike | null`
