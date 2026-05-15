# Seed Query 20260517 Gold V1

这批样本用于继续补齐第一版 SFT 训练集里 `chat / system / unsupported` 的主意图分布。

设计目标：

- 继续把 `main_intent` 从过度偏向 `qa` 往外拉平。
- 保持四层 gold 结构完整，直接可进入训练导出。
- 不让新增样本与当前冻结 held-out 混层。

包含文件：

- `chat_seed.json`
- `system_seed.json`
- `unsupported_seed.json`
