# Query Inputs

这个目录存放 Workflow + Answer 评测输入。

## 文件说明

- `seed_cases.jsonl`
  - 手工构造的最小种子集，适合本地验证与 rubric 校准
- `sampled_trace_cases.jsonl`
  - 从真实 trace 抽样后整理成统一 case 结构的输入集

## 维护约定

- 每行一个 JSON 对象
- 新增字段时，先同步更新 `schemas/case_schema.md`
- 真实 trace 回放时，如果 observability 摘要里没有最终回答正文，需要在整理 case 时补上 `answer_text`
