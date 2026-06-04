# Long-Term Memory Evaluation

`backend/evaluation/long_term_memory/` 是长期记忆存储质量评测专题模板。

当前先提供目录模板与统一入口占位，后续将围绕以下问题落地：

- 该写入的长期记忆是否被写入
- 不该写入的内容是否被误写
- `type / scope` 是否正确
- 是否保留可追溯的历史锚点

当前尚未实现具体 evaluator；执行框架将复用 `backend/evaluation/core/`。
