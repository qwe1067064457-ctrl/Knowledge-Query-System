# Working Memory Evaluation

`backend/evaluation/working_memory/` 是工作记忆连续性质量评测专题模板。

本轮只统一目录结构，不落业务 grader 实现。

## 目录说明

- `topic_config.py`
  - 后续将作为 `core.runner` 装配入口
- `graders/`
  - `rule_layer/`、`model_layer/`、`finalize_layer/` 的统一占位骨架
- `query_inputs/`
  - 后续存放工作记忆评测输入
- `rubrics/`
  - 后续定义维度、原因标签与边界
- `schemas/`
  - 后续定义 case/result 最小字段
- `reports/`
  - 后续存放评测输出
- `exports/`
  - 后续存放 benchmark 与中间导出物

## 当前状态

- 结构已按统一模板就位
- 业务实现待后续接入
