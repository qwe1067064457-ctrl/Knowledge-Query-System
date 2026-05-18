# MacBERT Baseline Dataset: task_shape

- source export: `C:\Users\HUAWEI\.codex\worktrees\db54\Skill-First-Hybrid-RAG\evaluation\intent\exports\v2\intent_training_v2_auto_20260518.jsonl`
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

### heldout

- rows: `9`
- labels: `{"none": 4, "single_question": 5}`

### train

- rows: `1358`
- labels: `{"compare": 41, "mixed": 45, "multi_question": 249, "none": 453, "single_question": 459, "summarize": 34, "verify": 77}`

### dev

- rows: `14`
- labels: `{"compare": 2, "multi_question": 1, "none": 8, "summarize": 2, "verify": 1}`
