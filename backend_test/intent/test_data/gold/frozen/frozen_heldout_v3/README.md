# frozen_heldout_v3

This dataset is the second frozen held-out set for the multi-signal SFT line.

Rules:

- do not tune rules against this dataset
- do not move these rows back into train or dev
- use it only after data freeze or model training
- if it exposes failures, record them separately instead of patching labels in place

Scope:

- `follow_up`
- `ask_source`
- `soft_doubt`
- `multi_question`
- `complex`
- `needs_clarification`

Files:

- `follow_up_frozen.json`
- `ask_source_frozen.json`
- `soft_doubt_frozen.json`
- `multi_question_frozen.json`
- `complex_frozen.json`
- `clarify_frozen.json`
