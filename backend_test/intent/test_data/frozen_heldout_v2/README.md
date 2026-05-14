# frozen_heldout_v2

This dataset is the first truly frozen held-out set after the current rule-tuning loop.

Rules:

- do not tune rules against this dataset
- use it only for validation after rule freeze or model training
- if it exposes failures, record them separately instead of immediately patching rules

Scope:

- `intent.qa.generic`
- `intent.qa.judgment`
- `challenge.soft_doubt`

Files:

- `qa_generic_frozen.json`
- `qa_judgment_frozen.json`
- `soft_doubt_frozen.json`
