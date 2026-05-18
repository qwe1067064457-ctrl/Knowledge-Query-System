# Intent Training Export V2

这个目录保留 `V2` 语义下的 intent 训练导出产物。

## 当前文件

- `intent_training_v2_topology_20260518.jsonl`
  - 旧 `gold` 样本按 `V2 schema` 重导出的结果
  - 重点是补 `resolved.task.topology` 与 `context_signals`
- `intent_training_v2_auto_20260518.jsonl`
  - 基于 `evaluation/intent/reports/v2_auto_annotations_20260518/` 自动重标结果导出的训练集
  - 属于 `V2 auto` 数据线

## 约定

- 不覆盖 `evaluation/intent/exports/` 根目录下现有 `intent_training_v1` 到 `intent_training_v7` 资产。
- `V1` 继续作为 baseline / teacher / regression anchor。
- `V2` 导出优先包含新的 `resolved.task.topology` 与 `context_signals` 语义。
- `V2 auto` 不等于人工复核 gold，它是规则链当前口径下的自动重标产物。
