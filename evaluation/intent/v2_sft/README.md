# Intent SFT V2

这条目录是 `V2 understanding` 的训练入口说明区。

它和现有 [multisignal_sft](/Users/genius/Developer/Ai_Project/Skill-First-Hybrid-RAG/evaluation/intent/multisignal_sft/README.md) 做物理隔离：

- `multisignal_sft`
  - `V1 baseline`
  - 只做 6 个 boundary signal
- `v2_sft`
  - 下一轮 `intent / task / context / safety` 主骨架训练线

## 当前代码入口

- [backend/intent/sft/v2/v2_label_spaces.py](/Users/genius/Developer/Ai_Project/Skill-First-Hybrid-RAG/backend/intent/sft/v2/v2_label_spaces.py)
- [backend/intent/sft/v2/v2_data.py](/Users/genius/Developer/Ai_Project/Skill-First-Hybrid-RAG/backend/intent/sft/v2/v2_data.py)
- [backend/intent/sft/v2/v2_eval.py](/Users/genius/Developer/Ai_Project/Skill-First-Hybrid-RAG/backend/intent/sft/v2/v2_eval.py)
- [backend/intent/sft/v2/v2_train_multitask.py](/Users/genius/Developer/Ai_Project/Skill-First-Hybrid-RAG/backend/intent/sft/v2/v2_train_multitask.py)

## 当前默认数据线

- `topology export`
  - [intent_training_v2_topology_20260518.jsonl](/Users/genius/Developer/Ai_Project/Skill-First-Hybrid-RAG/evaluation/intent/exports/v2/intent_training_v2_topology_20260518.jsonl)
- `auto export`
  - [intent_training_v2_auto_20260518.jsonl](/Users/genius/Developer/Ai_Project/Skill-First-Hybrid-RAG/evaluation/intent/exports/v2/intent_training_v2_auto_20260518.jsonl)

## 当前 heads

- `main_intent`
- `task_complexity`
- `task_shape`
- `task_topology`
- `modifiers`
- `context`
- `safety`

## 当前限制

- `V2 auto` 不是人工复核 gold
- 当前还没有独立 `V2 calibration` split
- 多标签 heads 目前临时用 `dev` 选阈值
- 这条线现在适合做下一轮原型训练，不适合直接当最终评估协议

## 20260519 补样本产物

- `backfill_20260519/`
  - 自动生成的 `V2` 补样本包
  - 包含 `split_manifest.json`
  - 包含 `review_candidates.jsonl`
  - 包含 `weak_train_candidates.jsonl`
- `benchmark_backfill_20260519/`
  - 面向 benchmark baseline 的补样本包
  - 在 `split_manifest.json` 之外，额外包含 `promotion_candidates.jsonl`
  - 以及 `synthetic_candidates.jsonl`
  - 用于补 `staged / parallel_subtasks` 等当前 gold 池缺口
- `benchmark_ready_20260519/`
  - benchmark backfill 的自动冻结产物
  - 包含 `gold_manifest.json`
  - 包含 `expanded_manifest.json`
  - 用于先跑 pre-benchmark 训练与评估

当前定位：

- 先补 `dev / calibration / heldout` 的候选分配
- 不直接宣布这些候选已经是 reviewed gold
- 允许训练线先用 manifest 跑 provisional prototype
