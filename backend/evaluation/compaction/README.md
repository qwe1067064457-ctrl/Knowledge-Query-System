# Compaction Evaluation

`backend/evaluation/compaction/` 是上下文压缩保真质量评测专题模板。

当前先提供目录模板与统一入口占位，后续将围绕以下问题落地：

- 关键信息是否保真
- 历史锚点是否仍可恢复
- 压缩后上下文是否仍足够支撑判断
- pre-compaction extraction 是否覆盖该保留内容

当前尚未实现具体 evaluator；执行框架将复用 `backend/evaluation/core/`。
