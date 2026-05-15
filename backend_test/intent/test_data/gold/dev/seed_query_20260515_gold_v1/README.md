# seed_query_20260515_gold_v1

This dataset is the first SFT-oriented gold expansion after `seed_query_20260514_gold_v1`.

Purpose:

- fill the most obvious label gaps before the first baseline
- add non-qa `main_intent` coverage
- add missing `task.shape` coverage
- add explicit `needs_clarification` and `challenge` training examples

Coverage:

- `chat`
- `system`
- `unsupported`
- `compare`
- `summarize`
- `needs_clarification`
- `challenge`

Files:

- `chat_seed.json`
- `system_seed.json`
- `unsupported_seed.json`
- `compare_seed.json`
- `summarize_seed.json`
- `clarify_seed.json`
- `challenge_seed.json`
