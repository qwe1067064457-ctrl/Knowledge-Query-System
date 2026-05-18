# V2 Auto Annotations 20260518

这份目录保存当前 `request understanding` 规则链在 `V2` 语义下，对现有样本做出的**全量自动重标结果**。

## 定位

- 这是 `V2 auto` 规则/数据线产物
- 不是人工复核后的最终金标
- 不回写 `backend_test/intent/test_data/`
- 只留在 `evaluation/intent/reports/`，保持和源数据物理隔离

## 文件结构

- `*.jsonl`
  - 每个数据集一份自动重标结果
- `summary.json`
  - 当前批次的总体统计

## 每条记录包含什么

- `gold`
  - 当前自动重标后的 `V2` 标签
- `legacy_gold`
  - 原始旧标签快照
- `comparison`
  - 新旧标签差异
- `migration_review`
  - 是否建议人工复核及原因

## 当前使用原则

- 可以作为后续 `V2 auto` 训练导出与规则数据分析输入
- 不直接替代 `test_data` 下的原始样本文件
- 若后续继续跑自动重标，应新建新的日期目录，不覆盖本目录
