# MacBERT Baseline Dataset: task_topology

- source export: `C:\Users\HUAWEI\.codex\worktrees\db54\Skill-First-Hybrid-RAG\evaluation\intent\exports\v2\intent_training_v2_auto_20260518.jsonl`
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

### heldout

- rows: `9`
- labels: `{"single": 9}`

### train

- rows: `1358`
- labels: `{"parallel_queries": 245, "parallel_subtasks": 4, "single": 1086, "staged": 23}`

### dev

- rows: `14`
- labels: `{"parallel_queries": 1, "single": 13}`
