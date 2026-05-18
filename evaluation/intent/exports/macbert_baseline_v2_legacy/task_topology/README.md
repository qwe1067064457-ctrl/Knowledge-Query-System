# MacBERT Baseline Dataset: task_topology

- source export: `evaluation\intent\exports\v2\intent_training_v2_topology_20260518.jsonl`
- model family: `hfl/chinese-macbert-base`
- format: one JSONL per split, each row contains `id / text / label / label_name / source_dataset / label_tier`

## Label Map

```json
{
  "single": 0,
  "parallel_queries": 1,
  "parallel_subtasks": 2,
  "staged": 3
}
```

## Split Summary

### train

- rows: `1358`
- labels: `{"parallel_queries": 241, "single": 1117}`

### dev

- rows: `14`
- labels: `{"single": 14}`

### heldout

- rows: `9`
- labels: `{"single": 9}`
