# MacBERT Baseline Dataset: modifier_ask_capability

- source export: `evaluation\intent\exports\v2\intent_training_v2_topology_20260518.jsonl`
- model family: `hfl/chinese-macbert-base`
- format: one JSONL per split, each row contains `id / text / label / label_name / source_dataset / label_tier`

## Label Map

```json
{
  "false": 0,
  "true": 1
}
```

## Split Summary

### train

- rows: `1358`
- labels: `{"false": 1347, "true": 11}`

### dev

- rows: `14`
- labels: `{"false": 12, "true": 2}`

### heldout

- rows: `9`
- labels: `{"false": 9}`
