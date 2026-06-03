# Workflow + Answer Evaluation

`evaluation/workflow_answer/` 是第一阶段评测主题目录，专门承接：

- `Knowledge retrieval` 质量评测
- `final answer` 质量评测
- 统一 case / result 结构
- 离线回放与线上抽样后的异步评测

这里不负责：

- monitoring 告警
- SLA / 性能看板
- compaction / memory extraction 专题评测

## 目录说明

- `query_inputs/`
  - 手工种子 case、抽样 trace case
- `rubrics/`
  - retrieval / answer 的维度定义与打分说明
- `graders/`
  - 规则 grader、LLM grader、人工复核路由
- `schemas/`
  - case/result 的最小字段约束
- `reports/`
  - 评测报告与汇总
- `exports/`
  - 冻结 benchmark、中间导出结果
- `evaluate_workflow_answer.py`
  - 从 case jsonl 跑到评分结果与 summary 的主脚本

## 推荐阅读顺序

1. `schemas/case_schema.md`
2. `schemas/result_schema.md`
3. `rubrics/retrieval_rubric.md`
4. `rubrics/answer_rubric.md`
5. `graders/README.md`
6. `query_inputs/README.md`

## 运行方式

```bash
python evaluation/workflow_answer/evaluate_workflow_answer.py evaluation/workflow_answer/query_inputs/seed_cases.jsonl --report-dir evaluation/workflow_answer/reports/manual_run
```

## 约定

- retrieval 只评 `Knowledge` 证据，不纳入长期记忆检索
- `core` 不作为 retrieval 证据来源竞争项，只在 answer 评测里参与上下文判断
- `like/dislike` 是辅助信号，不是真值标签
