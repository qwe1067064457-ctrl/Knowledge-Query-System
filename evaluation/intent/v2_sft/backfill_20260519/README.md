# V2 Sample Backfill Pack 20260519

## 定位

- 这是自动补样本产物，不是人工复核完成的正式 gold。
- `split_manifest.json` 提供 `dev / calibration / heldout` 的候选分配。
- `review_candidates.jsonl` 是评估样本 review 队列。
- `weak_train_candidates.jsonl` 是可低权重混训的 auto 弱监督候选。

## 当前摘要

```json
{
  "version": "2026-05-19",
  "task": "v2_sample_backfill",
  "targets": {
    "dev": 30,
    "calibration": 32,
    "heldout": 24
  },
  "input_files": {
    "topology_export": "/Users/genius/.codex/worktrees/653f/Skill-First-Hybrid-RAG/evaluation/intent/exports/v2/intent_training_v2_topology_20260518.jsonl",
    "auto_export": "/Users/genius/.codex/worktrees/653f/Skill-First-Hybrid-RAG/evaluation/intent/exports/v2/intent_training_v2_auto_20260518.jsonl"
  },
  "source_snapshot": {
    "rows": 1381,
    "existing_dev": 14,
    "existing_heldout": 9,
    "gold_train_pool": 109,
    "silver_changed_train_pool": 27
  },
  "proposed_splits": {
    "dev": 30,
    "calibration": 32,
    "heldout": 24
  },
  "review_queue": {
    "eval_review": 63,
    "weak_train": 27
  },
  "status_counts": {
    "legacy_seed": 23,
    "pending_review_gold": 63
  }
}
```

## 使用建议

- 先人工复核 `pending_review_gold`，再把通过样本正式冻结进 V2 split。
- `weak_train_candidates.jsonl` 不直接升级为 reviewed gold。
- 训练侧若要先跑 prototype，可把 `split_manifest.json` 作为 provisional split override 使用。

