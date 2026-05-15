# MacBERT Baseline Dataset: task_shape

- source export: `evaluation\intent\exports\intent_training_v7.jsonl`
- model family: `hfl/chinese-macbert-base`
- format: one JSONL per split, each row contains `id / text / label / label_name / source_dataset / label_tier`

## Label Map

```json
{
  "single_question": 0,
  "verify": 1,
  "compare": 2,
  "summarize": 3,
  "multi_question": 4
}
```

## Split Summary

### train

- rows: `855`
- labels: `{"compare": 40, "multi_question": 241, "single_question": 448, "summarize": 35, "verify": 91}`

### dev

- rows: `6`
- labels: `{"compare": 2, "summarize": 2, "verify": 2}`

### heldout

- rows: `9`
- labels: `{"verify": 9}`
