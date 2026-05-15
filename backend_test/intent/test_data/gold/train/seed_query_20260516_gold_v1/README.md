# seed_query_20260516_gold_v1

This dataset is the second large-batch SFT-oriented gold expansion derived from
`intent_query_full_set.md`.

Purpose:

- move the training set from sample-level validation toward baseline-trainable scale
- thicken the most underrepresented `task.shape` buckets
- add more non-qa rows and explicit negative boundaries for `soft_doubt`
- keep all rows in the four-layer gold format used by the existing export pipeline

Primary coverage:

- `compare`
- `summarize`
- `multi_question`
- `soft_doubt=false` boundary negatives

Secondary coverage:

- `chat`
- `system`
- `unsupported`
- `needs_clarification`
- `challenge`

Files:

- `compare_seed.json`
- `summarize_seed.json`
- `multi_question_seed.json`
- `soft_doubt_boundary_seed.json`
- `chat_seed.json`
- `system_seed.json`
- `unsupported_seed.json`
- `clarify_seed.json`
- `challenge_seed.json`
