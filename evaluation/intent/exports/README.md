# Exports

`exports/` 存放从评估数据衍生出来的训练集和 baseline 数据包。

## 当前内容

- `intent_training_v1.jsonl` 到 `intent_training_v7.jsonl`
  - 不同阶段导出的训练集版本
- `macbert_baseline_v1/`
  - MacBERT baseline 数据包

## 使用建议

- 新导出的训练集继续按版本递增，避免覆盖旧版本
- 某个版本如果已经废弃，不要直接删除，先确认是否仍被文档或脚本引用
- baseline 数据包内部应自带 README，说明任务划分、标签和 split

## 当前判断

- `intent_training_v1` 到 `v7` 属于阶段性导出资产，保留在这里是合理的
- `macbert_baseline_v1/` 已经是一个相对独立的数据包，可以继续自成子目录维护
