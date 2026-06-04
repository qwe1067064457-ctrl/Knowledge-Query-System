# Working Memory Evaluation

`backend/evaluation/working_memory/` 用于评估 `Session Working Memory` 的执行连续性质量。

## 目录说明

- `topic_config.py`
  - 将本专题 graders 装配成 `core.runner` 可执行配置
- `graders/`
  - `rule_layer/`：结构性与硬约束判断
  - `model_layer/`：语义维度 LLM grader 与 runtime
  - `finalize_layer/`：fallback、聚合、人工复核标记
- `query_inputs/`
  - 手工 seed case 与后续 trace 抽样输入
- `rubrics/`
  - 维度定义、原因标签与边界说明
- `schemas/`
  - case/result 最小字段
- `reports/`
  - 评测输出
- `exports/`
  - benchmark 冻结集与中间导出物

## 当前第一版范围

- `continuity_support`
- `key_state_capture`
- `noise_control`
- `freshness`
- `handoff_utility`

## 运行方式

```bash
python backend/evaluation/working_memory/evaluate_working_memory.py backend/evaluation/working_memory/query_inputs/seed_cases.jsonl --report-dir backend/evaluation/working_memory/reports/manual_run
```
