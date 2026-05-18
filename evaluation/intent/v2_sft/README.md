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
