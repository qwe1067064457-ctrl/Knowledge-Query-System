# MacBERT Baseline Dataset: main_intent

- source export: `C:\Users\HUAWEI\.codex\worktrees\db54\Skill-First-Hybrid-RAG\evaluation\intent\exports\v2\intent_training_v2_auto_20260518.jsonl`
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

### heldout

- rows: `9`
- labels: `{"chat": 4, "qa": 5}`

### train

- rows: `1358`
- labels: `{"chat": 428, "qa": 905, "system": 2, "unsupported": 23}`

### dev

- rows: `14`
- labels: `{"chat": 7, "qa": 6, "unsupported": 1}`
