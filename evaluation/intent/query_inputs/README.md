# Query Inputs

`query_inputs/` 存放 intent 评估使用的输入集合。

## 当前内容

- `intent_query_full_set.md`
  - 人工整理的 query 全量清单，适合阅读和回顾覆盖面
- `query_list_benchmark_v1.json`
  - 基准评估输入
- `seed_query_20260514.jsonl`
  - 第一批种子 query
- `seed_query_20260515_router_augmented.jsonl`
  - 在 router 视角增强后的种子 query
- `seed_query_20260517_router_augmented_v2.jsonl`
  - 为 multi-signal `dev` 回补准备的第二批边界 query
- `heldout_judgment_soft_doubt_20260514.jsonl`
  - heldout 判断类样本
- `heldout_multisignal_20260517_v3.jsonl`
  - 为 `frozen_heldout_v3` 准备的 6 signal heldout 输入源

## 使用建议

- 想看“评估到底测了什么”，先读 `intent_query_full_set.md`
- 想跑脚本，优先使用 json 或 jsonl 输入
- 新增输入集时，文件名尽量带日期或版本，避免覆盖旧资产
