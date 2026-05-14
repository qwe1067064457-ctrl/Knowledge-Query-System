# Intent SFT Preparation

> 如果你是新开一个对话，或需要一份可直接接手当前阶段的完整文档，请先读：
> [intent_sft_delivery.md](C:/Users/HUAWEI/.codex/worktrees/2a18/Skill-First-Hybrid-RAG/notes/intent/intent_sft_delivery.md)

## 1. 当前目标

当前 intent 模块进入 SFT 准备阶段后的目标不是“让模型接管全部逻辑”，而是先做一个轻量、边界清楚的小模型路由器。

第一版建议模型负责：

- `main_intent`
- `follow_up / ask_source / challenge / soft_doubt / needs_clarification`
- 关键 `task.shape`
  - `single_question`
  - `verify`
  - `compare`
  - `summarize`
  - `multi_question`

`control` 仍优先由规则映射，不建议第一版直接训练 `route / mode` 作为主监督目标。

---

## 2. 当前数据资产

### 可训练 gold

- [seed_query_20260514_gold_v1](/C:/Users/HUAWEI/.codex/worktrees/2a18/Skill-First-Hybrid-RAG/backend_test/intent/test_data/seed_query_20260514_gold_v1)

### 项目级 query 输入源

- [intent_query_full_set.md](C:/Users/HUAWEI/.codex/worktrees/2a18/Skill-First-Hybrid-RAG/evaluation/intent/query_inputs/intent_query_full_set.md)
- [seed_query_20260514.jsonl](C:/Users/HUAWEI/.codex/worktrees/2a18/Skill-First-Hybrid-RAG/evaluation/intent/query_inputs/seed_query_20260514.jsonl)
- [heldout_judgment_soft_doubt_20260514.jsonl](C:/Users/HUAWEI/.codex/worktrees/2a18/Skill-First-Hybrid-RAG/evaluation/intent/query_inputs/heldout_judgment_soft_doubt_20260514.jsonl)

### 冻结 held-out

- [frozen_heldout_v2](/C:/Users/HUAWEI/.codex/worktrees/2a18/Skill-First-Hybrid-RAG/backend_test/intent/test_data/frozen_heldout_v2)

### 规则级监督

- [rule_supervision_approved_v1.jsonl](/C:/Users/HUAWEI/.codex/worktrees/2a18/Skill-First-Hybrid-RAG/evaluation/intent/rule_supervision_approved_v1.jsonl)

### 当前导出文件

- [intent_training_v1.jsonl](/C:/Users/HUAWEI/.codex/worktrees/2a18/Skill-First-Hybrid-RAG/evaluation/intent/exports/intent_training_v1.jsonl)

---

## 3. 导出字段规范

当前训练导出行包含：

- `id`
- `batch`
- `split`
- `input`
- `evidence`
- `resolved`
- `control`
- `metadata`

其中 `metadata` 当前固定包含：

- `source_dataset`
- `source_query_id`
- `label_tier`
- `label_source`
- `review_status`
- `difficulty`
- `is_heldout`
- `is_strict_rule_supervision`

---

## 4. 数据分层建议

当前建议采用三层口径：

### gold

- 人工或四层 gold 明确确认
- 可直接进入 train / dev / held-out

### silver

- 规则或 skill 预标
- 需要抽样复核
- 可用于扩训练规模，但不应和 gold 混成同权重

### weak

- 仅规则推断
- 适合蒸馏或辅助训练
- 不适合作为高权重监督

---

## 5. 划分建议

第一版建议：

- `train`
  - 以当前 gold 为主
- `dev`
  - 从非冻结 gold 中切一小部分，不和 train 混用
- `heldout`
  - 固定使用 [frozen_heldout_v2](/C:/Users/HUAWEI/.codex/worktrees/2a18/Skill-First-Hybrid-RAG/backend_test/intent/test_data/frozen_heldout_v2)

约束：

- `frozen_heldout_v2` 不得参与规则调优
- `frozen_heldout_v2` 不得回填进训练集

---

## 6. 模型建议

如果目标是“意图识别不太重但精度高”，第一版优先：

- `BERT` / `RoBERTa` 类 encoder classifier

不建议第一版直接上大生成模型做主路由，原因是：

- 成本更高
- 输出更难约束
- 当前标签更适合分类头

---

## 7. 下一步

1. 从当前 `intent_training_v1.jsonl` 切出 `train/dev`
2. 明确第一版模型的输出标签集合
3. 为 `silver / weak` 数据准备后续增量入口
4. 训练前固定 `frozen_heldout_v2`，不再修改
