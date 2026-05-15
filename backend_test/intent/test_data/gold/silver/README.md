# Intent Silver Datasets

这里存放由 `campaign` 通过 `auto-uplift` 批量提升出来的 `silver` 四层样本。

## 作用

- 作为 `gold` 之外的主扩量层
- 降低继续用 LLM 手工构建 full gold 的 token 成本
- 让现有 `classifier -> resolver -> control` 直接充当自动标注器

## 约束

- `silver` 可以进入 `train`
- `silver` 不进入 `dev`
- `silver` 不进入 `frozen held-out`
- `silver` 的标签可信度默认低于 `gold`

## 当前样本

- `intent_query_full_set_campaign_v1_silver_v1`
  - 来源：`campaign/intent_query_full_set_campaign_v1`
  - 方式：当前规则流水线自动 uplift
  - 当前默认用于训练导出
- `seed_query_20260514_campaign_v1_silver_v1`
  - 来源：`campaign/seed_query_20260514_campaign_v1`
  - 方式：当前规则流水线自动 uplift
- `query_list_campaign_v1_silver_v1`
  - 来源：`campaign/query_list_campaign_v1`
  - 方式：当前规则流水线自动 uplift
- `seed_query_20260515_campaign_v2_silver_v1`
  - 来源：`campaign/seed_query_20260515_campaign_v2`
  - 方式：当前规则流水线自动 uplift
  - 这条链已于 `2026-05-15` 重建为干净版本

## 当前默认导出

- `evaluation/intent/export_intent_training_set.py` 会自动扫描本目录下的所有 `silver` 子目录
- 当前训练导出文件：`evaluation/intent/exports/intent_training_v7.jsonl`
