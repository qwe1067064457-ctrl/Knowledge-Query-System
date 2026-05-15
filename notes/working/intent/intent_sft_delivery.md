# Intent SFT Delivery

这份文档面向新对话或新接手开发者，说明当前 `intent` 模块在进入小模型 baseline 前，数据与规则资产已经交付到什么程度。

## 当前数据层级

### 原料层

- `evaluation/intent/query_inputs/intent_query_full_set.md`
- `evaluation/intent/query_inputs/seed_query_20260514.jsonl`
- `evaluation/intent/query_inputs/seed_query_20260515_router_augmented.jsonl`

说明：

- 这些是 `seed / query` 输入源
- 不直接参与最终 benchmark

### 增强层

- `backend_test/intent/test_data/campaign/seed_query_20260514_campaign_v1`
- `backend_test/intent/test_data/campaign/seed_query_20260515_campaign_v2`
- `backend_test/intent/test_data/campaign/intent_query_full_set_campaign_v1`
- `backend_test/intent/test_data/campaign/query_list_campaign_v1`

说明：

- 这些是 `campaign / augmentation` 池
- 可用于压测、找边界、提升成 `gold` 或 `silver`
- 不直接视为正式训练集

### 训练层

#### gold train

- `backend_test/intent/test_data/gold/train/seed_query_20260514_gold_v1`
- `backend_test/intent/test_data/gold/train/seed_query_20260515_gold_v2`
- `backend_test/intent/test_data/gold/train/seed_query_20260516_gold_v1`
- `backend_test/intent/test_data/gold/train/seed_query_20260517_gold_v1`

#### silver train

- `backend_test/intent/test_data/gold/silver/intent_query_full_set_campaign_v1_silver_v1`
- `backend_test/intent/test_data/gold/silver/seed_query_20260515_campaign_v2_silver_v1`
- `backend_test/intent/test_data/gold/silver/seed_query_20260514_campaign_v1_silver_v1`
- `backend_test/intent/test_data/gold/silver/query_list_campaign_v1_silver_v1`

### 开发验证层

- `backend_test/intent/test_data/gold/dev/seed_query_20260515_gold_v1`

### 冻结 benchmark

- `backend_test/intent/test_data/gold/frozen/frozen_heldout_v2`

## 当前导出

- `evaluation/intent/exports/intent_training_v7.jsonl`
- `evaluation/intent/exports/macbert_baseline_v1/`

语义：

- `train`：正式训练样本
- `dev`：开发验证样本
- `heldout`：最终 benchmark

## 当前工程结论

- 规则层已经完成第一阶段收口，可作为 teacher / guardrail / data factory
- `seed query` 已回到上游原料层
- `campaign / silver / gold / dev / frozen` 已分层
- `20260515` 这一支增强链已于 `2026-05-15` 重建为干净版本
- 当前可以进入第一版 `macbert-base` baseline 准备，但仍建议优先使用 `gold + silver` 分层训练

## 当前规模

- `intent_training_v7.jsonl`
  - `train = 1358`
  - `dev = 14`
  - `heldout = 9`
- `macbert_baseline_v1`
  - `soft_doubt`
  - `task_shape`

## 当前已知缺口

- 第一版 `dev` 在 `soft_doubt` 任务里暂时没有正例
- 这意味着 baseline 已经可跑，但下一步仍应补一批 `soft_doubt=true` 的 `dev` 样本
