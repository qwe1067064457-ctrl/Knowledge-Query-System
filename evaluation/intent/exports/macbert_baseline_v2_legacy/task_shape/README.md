# MacBERT Baseline Dataset: task_shape

- source export: `evaluation\intent\exports\v2\intent_training_v2_topology_20260518.jsonl`
- model family: `hfl/chinese-macbert-base`
- format: one JSONL per split, each row contains `id / text / label / label_name / source_dataset / label_tier`

## Label Map

```json
{
  "single_question": 0,
  "multi_question": 1,
  "compare": 2,
  "summarize": 3,
  "extract": 4,
  "verify": 5,
  "mixed": 6,
  "none": 7
}
```

## Split Summary

### train

- rows: `1358`
- labels: `{"compare": 40, "mixed": 44, "multi_question": 241, "none": 459, "single_question": 448, "summarize": 35, "verify": 91}`

### dev

- rows: `14`
- labels: `{"compare": 2, "none": 8, "summarize": 2, "verify": 2}`

### heldout

- rows: `9`
- labels: `{"verify": 9}`
