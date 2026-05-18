# Intent Auto-Uplift Silver

这份文档记录当前 `intent` 模块的 `auto-uplift` 数据生产线。

## 目标

解决两个问题：

1. `seed/campaign` 很多，但真正可训练的 `gold` 太少
2. 继续把每条样本都手工抬成 full gold，耗时长、token 成本高

因此现在引入一层新的训练资产：

- `silver`

## 生产线

当前分层：

1. `seed`
2. `campaign`
3. `auto-uplift silver`
4. `gold`
5. `dev / frozen held-out`

对应理解：

- `seed`：原料池
- `campaign`：增强池 / 压测池
- `silver`：批量训练层
- `gold`：高质量高权重训练层
- `dev/frozen`：验证层

## 当前实现

脚本：

- `evaluation/intent/auto_uplift_silver.py`

实现方式：

- 输入：一个 `campaign` 数据集目录
- 处理：
  - 逐条读取 `input.user_query` 和 `history`
  - 走当前 `classifier -> resolver -> control`
  - 自动回填四层结构
- 输出：
  - 一个新的 `gold/silver/*` 数据集目录
  - 每条样本带：
    - `label_tier = silver`
    - `label_source = auto_uplift_rule_pipeline`
    - `review_status = draft`

## 当前数据集

- 主推荐：
  - `backend_test/intent/test_data/gold/silver/intent_query_full_set_campaign_v1_silver_v1`
  - 来源：`backend_test/intent/test_data/campaign/intent_query_full_set_campaign_v1`
  - 规模：`1137` 条，`8` 个 batch
- 追加扩量：
  - `backend_test/intent/test_data/gold/silver/seed_query_20260514_campaign_v1_silver_v1`
  - 来源：`backend_test/intent/test_data/campaign/seed_query_20260514_campaign_v1`
  - 规模：`40` 条
  - `backend_test/intent/test_data/gold/silver/query_list_campaign_v1_silver_v1`
  - 来源：`backend_test/intent/test_data/campaign/query_list_campaign_v1`
  - 规模：`16` 条
- 历史实验：
  - `backend_test/intent/test_data/gold/silver/seed_query_20260515_campaign_v2_silver_v1`
  - 来源：`backend_test/intent/test_data/campaign/seed_query_20260515_campaign_v2`
  - 说明：这条链已在 `2026-05-15` 重建为干净版本，当前也已可进入默认训练导出

## 质量护栏

`auto-uplift` 现在会跳过一种明显损坏的 query：

- 去掉空白后只剩 `?` / `？`

目的不是做复杂清洗，而是避免把已经损坏的 `campaign` 文本继续放大成训练 `silver`。  
这条护栏在重建 `20260515` 之前已经帮助我们阻止坏链继续扩散，后续仍建议保留。

## 导出规则

训练导出脚本：

- `evaluation/intent/export_intent_training_set.py`

当前默认行为：

- `gold/train` -> `train`
- `gold/silver` -> `train`
- `gold/dev` -> `dev`
- `gold/frozen` -> `heldout`

也就是说，`silver` 已经进入正式训练导出，但不会进入 `dev` 或 `heldout`。

## 当前默认训练导出状态

- 导出文件：`evaluation/intent/exports/intent_training_v7.jsonl`
- 当前规模：
  - `train = 1358`
  - `dev = 14`
  - `heldout = 9`
- `train` 中：
  - `gold = 109`
  - `silver = 1249`

## 使用原则

- `gold`：高质量、高权重
- `silver`：主扩量层、低于 `gold` 的信任级别
- `frozen held-out`：永不反向调优

## 下一步

1. 继续把更多 `campaign` 批量 uplift 成 `silver`
2. 再从 `silver` 中抽高价值边界样本升级成 `gold`
3. 训练时采用：
   - `gold` 高权重
   - `silver` 主训练量
status: legacy-reference
related_current_doc: notes/intent/intent_v2_migration.md
scope: silver auto uplift history
