# SFT Gold Expansion 20260517

## 本轮目的

这一轮专门补 `chat / system / unsupported`，同时把第一版 `dev` 正式切出来。

## 新增训练 gold

新增目录：

- `backend_test/intent/test_data/gold/train/seed_query_20260517_gold_v1`

包含：

- `chat_seed.json`：6 条
- `system_seed.json`：6 条
- `unsupported_seed.json`：6 条

## 第一版 dev

按照现有 split policy，本轮把一个完整 seed 家族整体移出训练池：

- `backend_test/intent/test_data/gold/dev/seed_query_20260515_gold_v1`

这样可以满足：

- 同一 seed 家族不跨 `train / dev`
- `dev` 里保留 `chat / system / unsupported / compare / summarize / clarify / challenge` 的混合覆盖

## 当前语义约束

- `seed query` 仍然只是原料，不直接参与最终 benchmark
- `campaign` 仍然只是增强池和候选池
- 训练成品只认 `gold/train`
- 最终 benchmark 只认 `gold/frozen`
