# MacBERT Baseline Dataset: task_complexity

- source export: `C:\Users\HUAWEI\.codex\worktrees\db54\Skill-First-Hybrid-RAG\evaluation\intent\exports\v2\intent_training_v2_auto_20260518.jsonl`
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

### heldout

- rows: `9`
- labels: `{"simple": 9}`

### train

- rows: `1358`
- labels: `{"complex": 169, "compound": 249, "simple": 940}`

### dev

- rows: `14`
- labels: `{"complex": 4, "compound": 1, "simple": 9}`
