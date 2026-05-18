# MacBERT Baseline Dataset: main_intent

- source export: `evaluation\intent\exports\v2\intent_training_v2_topology_20260518.jsonl`
- model family: `hfl/chinese-macbert-base`
- format: one JSONL per split, each row contains `id / text / label / label_name / source_dataset / label_tier`

## Label Map

```json
{
  "qa": 0,
  "chat": 1,
  "system": 2,
  "unsupported": 3
}
```

## Split Summary

### train

- rows: `1358`
- labels: `{"chat": 412, "qa": 903, "system": 13, "unsupported": 30}`

### dev

- rows: `14`
- labels: `{"chat": 2, "qa": 8, "system": 2, "unsupported": 2}`

### heldout

- rows: `9`
- labels: `{"qa": 9}`
