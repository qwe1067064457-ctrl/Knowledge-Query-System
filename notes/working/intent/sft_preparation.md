# Intent SFT Preparation

这份文档是 working 入口，记录当前 intent 小模型训练前的准备状态。

更完整的交付请优先看：

- `notes/working/intent/intent_sft_delivery.md`

## 当前主要数据资产

### query 输入源

- `evaluation/intent/query_inputs/intent_query_full_set.md`
- `evaluation/intent/query_inputs/seed_query_20260514.jsonl`
- `evaluation/intent/query_inputs/seed_query_20260515_router_augmented.jsonl`

### train gold

- `backend_test/intent/test_data/gold/train/seed_query_20260514_gold_v1`
- `backend_test/intent/test_data/gold/train/seed_query_20260515_gold_v2`
- `backend_test/intent/test_data/gold/train/seed_query_20260516_gold_v1`
- `backend_test/intent/test_data/gold/train/seed_query_20260517_gold_v1`

### dev gold

- `backend_test/intent/test_data/gold/dev/seed_query_20260515_gold_v1`

### frozen held-out

- `backend_test/intent/test_data/gold/frozen/frozen_heldout_v2`

### 训练导出

- `evaluation/intent/exports/intent_training_v7.jsonl`
- `evaluation/intent/exports/macbert_baseline_v1/`

## 当前判断

- `seed query` 只作为原料和增强输入，不直接进入最终 benchmark
- `campaign` 是增强池，不是正式训练集
- `gold/train` 是训练成品
- `gold/dev` 是开发验证集
- `gold/frozen` 是最终 benchmark
- `gold/silver` 已经进入默认训练导出

## 当前 baseline 输入

- `macbert_baseline_v1/soft_doubt`
- `macbert_baseline_v1/task_shape`

说明：

- 这是按 `hfl/chinese-macbert-base` 第一版 baseline 准备的任务级输入
- 当前已知缺口是：`dev` 中 `soft_doubt` 暂时没有正例

## 下一步

- 继续补齐 `main_intent` 分布
- 继续加厚 `follow_up / ask_source / soft_doubt` 的正负边界
- 在 `train/dev/heldout` 三段都稳定后，再进入 baseline 训练
