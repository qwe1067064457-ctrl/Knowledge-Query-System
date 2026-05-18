# SFT Gold Expansion 20260515 v2

这轮数据扩充围绕 `20260515` 这条增强链展开，目标是补足：

- `follow_up`
- `ask_source`
- `soft_doubt`
- `multi_question`

## 数据入口

- `evaluation/intent/query_inputs/seed_query_20260515_router_augmented.jsonl`

## 产物

- campaign:
  - `backend_test/intent/test_data/campaign/seed_query_20260515_campaign_v2`
- train gold:
  - `backend_test/intent/test_data/gold/train/seed_query_20260515_gold_v2`

## 后续修正

`2026-05-15` 晚些时候确认这条链曾出现中文被写成纯问号的历史问题。当前版本已经重建完成：

- `router_augmented` 已恢复为干净中文
- `campaign_v2` 已重新生成
- `gold_v2` 已从干净 campaign 重新回填

因此现在这份文档对应的就是**重建后的干净链**，不再是损坏版本。
status: legacy-reference
related_current_doc: notes/intent/test_data_generate/campaigns_and_results.md
scope: sft gold expansion snapshot
