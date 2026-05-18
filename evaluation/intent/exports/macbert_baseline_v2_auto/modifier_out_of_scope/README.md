# MacBERT Baseline Dataset: modifier_out_of_scope

- source export: `C:\Users\HUAWEI\.codex\worktrees\db54\Skill-First-Hybrid-RAG\evaluation\intent\exports\v2\intent_training_v2_auto_20260518.jsonl`
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

### heldout

- rows: `9`
- labels: `{"false": 9}`

### train

- rows: `1358`
- labels: `{"false": 1335, "true": 23}`

### dev

- rows: `14`
- labels: `{"false": 13, "true": 1}`
