# 20260516 SFT Gold Expansion

## 1. 文档定位

这是一份本轮批量扩样的增量记录。

它不替代：

- `intent_sft_delivery.md`
- `sft_preparation.md`
- `sft_label_spec.md`
- `sft_split_policy.md`
- `sft_eval_protocol.md`

它只回答一件事：

> 2026-05-16 这一轮，基于 `intent_query_full_set.md`，到底补了哪些训练 gold。

---

## 2. 新增数据集

- `backend_test/intent/test_data/gold/train/seed_query_20260516_gold_v1`

这是第二批面向 SFT 的大规模 gold 扩样。

相比 `20260515` 的“第一轮补缺口”，这批的目标更明确：

- 直接提升可训练规模
- 按 shape 和边界负例集中补桶
- 不再一类只补 2 条

---

## 3. 本批次覆盖

主补项：

- `compare`
- `summarize`
- `multi_question`
- `soft_doubt=false` 边界负例

顺带加厚：

- `chat`
- `system`
- `unsupported`
- `needs_clarification`
- `challenge`

文件清单：

- `compare_seed.json`
- `summarize_seed.json`
- `multi_question_seed.json`
- `soft_doubt_boundary_seed.json`
- `chat_seed.json`
- `system_seed.json`
- `unsupported_seed.json`
- `clarify_seed.json`
- `challenge_seed.json`

---

## 4. 与 SFT 协议的关系

这批扩样直接服务于当前 working 协议里最缺的几类：

- `task.shape.compare`
- `task.shape.summarize`
- `task.shape.multi_question`
- `soft_doubt` 的高质量负例

也就是说，这批样本的主要作用不是继续修规则，而是让第一版 baseline 更像“能训的训练集”。

---

## 5. 导出接入

默认训练导出源已经接入：

- `evaluation/intent/export_intent_training_set.py`

对应导出建议使用：

- `evaluation/intent/exports/intent_training_v3.jsonl`

---

## 6. 当前判断

这一轮之后，训练集会明显比 `intent_training_v2.jsonl` 更像样，但仍然不能直接等价成“正式完整 intent SFT 数据集”。

原因仍然是：

- 总规模还不够大
- `main_intent` 依然偏斜
- `dev` 尚未正式切分
- 冻结 held-out 还需要继续保持不参与调优

所以这批扩样的意义是：

> 把训练集从“样板级”推进到“baseline 前夜”，而不是直接宣布样本已经充足。
