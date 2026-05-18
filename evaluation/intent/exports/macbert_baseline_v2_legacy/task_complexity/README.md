# MacBERT Baseline Dataset: task_complexity

- source export: `evaluation\intent\exports\v2\intent_training_v2_topology_20260518.jsonl`
- model family: `hfl/chinese-macbert-base`
- format: one JSONL per split, each row contains `id / text / label / label_name / source_dataset / label_tier`

## Label Map

```json
{
  "simple": 0,
  "compound": 1,
  "complex": 2
}
```

## Split Summary

### train

- rows: `1358`
- labels: `{"complex": 159, "compound": 233, "simple": 966}`

### dev

- rows: `14`
- labels: `{"simple": 14}`

### heldout

- rows: `9`
- labels: `{"simple": 9}`
