# V2 Benchmark Ready 20260519

## 定位

- 这是自动冻结产物，不是正式人工 reviewed benchmark。
- `gold_manifest.json` 只使用原 gold-like split 候选。
- `expanded_manifest.json` 额外吸收 promotion 和 synthetic 候选，用于先跑更接近 benchmark 的训练与评估。
- `expanded_override_rows.jsonl` 物化了 promotion 的 auto 标签和 synthetic 样本，供导 bundle 时叠加输入。

## 当前摘要

```json
{
  "version": "2026-05-19",
  "task": "v2_benchmark_auto_freeze",
  "source_backfill_dir": "/Users/genius/.codex/worktrees/653f/Skill-First-Hybrid-RAG/evaluation/intent/v2_sft/benchmark_backfill_20260519",
  "gold_only": {
    "entries": 132,
    "dev": 42,
    "calibration": 48,
    "heldout": 42
  },
  "expanded": {
    "entries": 194,
    "dev": 49,
    "calibration": 90,
    "heldout": 55
  },
  "decision_counts": {
    "accept_gold_like": 132,
    "accept_auto_promotion": 27,
    "accept_synthetic_gap_fill": 35
  },
  "boundary": {
    "gold_only_is_higher_confidence": true,
    "expanded_contains_auto_and_synthetic": true,
    "formal_human_review_still_required_for_official_benchmark": true
  },
  "helper_files": {
    "topology_export": "/Users/genius/.codex/worktrees/653f/Skill-First-Hybrid-RAG/evaluation/intent/exports/v2/intent_training_v2_topology_20260518.jsonl",
    "auto_export": "/Users/genius/.codex/worktrees/653f/Skill-First-Hybrid-RAG/evaluation/intent/exports/v2/intent_training_v2_auto_20260518.jsonl",
    "expanded_override_rows": "expanded_override_rows.jsonl"
  }
}
```

## 使用边界

- `gold_manifest.json` 适合先跑高置信度 pre-benchmark。
- `expanded_manifest.json` 适合先跑 coverage 更完整的 pre-benchmark。
- 如果要宣称正式 benchmark，仍需人工复核后重新冻结。

