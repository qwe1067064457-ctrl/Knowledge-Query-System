# Working Memory Evaluation

`backend/evaluation/working_memory/` 是工作记忆连续性质量评测专题模板。

当前先提供目录模板与统一入口占位，后续将围绕以下问题落地：

- 是否支撑执行连续性
- 关键状态是否被正确保留
- 是否引入无关噪声
- 过期状态是否及时淘汰

当前尚未实现具体 evaluator；执行框架将复用 `backend/evaluation/core/`。
