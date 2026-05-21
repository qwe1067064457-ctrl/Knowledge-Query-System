# V2 Benchmark Backfill Pack 20260519

## 定位

- 这是自动补样本产物，不是人工复核完成的正式 gold。
- `split_manifest.json` 提供 `dev / calibration / heldout` 的候选分配。
- `review_candidates.jsonl` 是评估样本 review 队列。
- `weak_train_candidates.jsonl` 是可低权重混训的 auto 弱监督候选。
- `promotion_candidates.jsonl` 是需要 review 后才能晋升到 benchmark split 的 auto 候选。
- `synthetic_candidates.jsonl` 是为补齐剩余 benchmark 缺口自动生成的合成候选。

## 当前摘要

```json
{
  "version": "2026-05-19",
  "task": "v2_benchmark_backfill",
  "profile": "benchmark",
  "targets": {
    "dev": 42,
    "calibration": 48,
    "heldout": 42
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
    "dev": 42,
    "calibration": 48,
    "heldout": 42
  },
  "review_queue": {
    "eval_review": 109,
    "weak_train": 27
  },
  "promotion_queue": 27,
  "synthetic_queue": 35,
  "status_counts": {
    "legacy_seed": 23,
    "pending_review_gold": 109
  },
  "gap_summary": {
    "dev": {
      "task_complexity": {
        "compound": 1
      },
      "task_shape": {
        "mixed": 1
      },
      "task_topology": {
        "staged": 2,
        "parallel_subtasks": 2
      }
    },
    "calibration": {
      "task_complexity": {
        "complex": 8,
        "compound": 4
      },
      "task_shape": {
        "multi_question": 6,
        "compare": 6,
        "summarize": 3,
        "mixed": 3
      },
      "task_topology": {
        "parallel_queries": 6,
        "staged": 2,
        "parallel_subtasks": 2
      },
      "modifiers": {
        "challenge": 2,
        "soft_doubt": 2,
        "needs_clarification": 2
      },
      "context": {
        "clarify_hint": 2
      }
    },
    "heldout": {
      "task_complexity": {
        "compound": 4
      },
      "task_shape": {
        "mixed": 2
      },
      "task_topology": {
        "parallel_queries": 1,
        "staged": 2,
        "parallel_subtasks": 2
      }
    }
  },
  "remaining_gap_after_promotion": {
    "dev": {
      "task_complexity": {
        "compound": 1
      },
      "task_shape": {
        "mixed": 1
      },
      "task_topology": {
        "parallel_subtasks": 2
      }
    },
    "calibration": {
      "task_complexity": {
        "compound": 4
      },
      "task_shape": {
        "multi_question": 6,
        "compare": 6
      },
      "task_topology": {
        "parallel_queries": 6,
        "parallel_subtasks": 2
      },
      "modifiers": {
        "challenge": 2,
        "soft_doubt": 2,
        "needs_clarification": 1
      },
      "context": {
        "clarify_hint": 1
      }
    },
    "heldout": {
      "task_topology": {
        "parallel_queries": 1
      }
    }
  }
}
```

## 使用建议

- 先人工复核 `pending_review_gold`，再把通过样本正式冻结进 V2 split。
- `weak_train_candidates.jsonl` 不直接升级为 reviewed gold。
- `promotion_candidates.jsonl` 里的样本只有在复核通过并确认采用 `proposed_labels` 后，才可进入 benchmark split。
- `synthetic_candidates.jsonl` 里的样本默认不进入训练，需要单独复核后再决定是否纳入 benchmark eval。
- 训练侧若要先跑 prototype，可把 `split_manifest.json` 作为 provisional split override 使用。

