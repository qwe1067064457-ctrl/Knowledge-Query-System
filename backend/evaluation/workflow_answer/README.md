# Workflow + Answer Evaluation

`backend/evaluation/workflow_answer/` 是第一阶段评测主题目录，专门承接：

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
- `topic_config.py`
  - 把本专题装配成 `core.runner` 可消费的 config
- `rule_impl.py`
  - 本专题的规则层组合入口
- `model_impl.py`
  - 本专题的模型层组合入口
- `finalize_impl.py`
  - 本专题的 finalize 入口，负责兜底、聚合、人工复核标记
- `graders/`
  - `rule_layer/`：retrieval / answer 的底层规则实现
  - `model_layer/`：retrieval / answer 的底层模型实现与 runtime
  - `finalize_layer/`：底层聚合与人工复核逻辑
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
5. `topic_config.py`
6. `rule_impl.py`
7. `model_impl.py`
8. `finalize_impl.py`
9. `query_inputs/README.md`

## 运行方式

```bash
python backend/evaluation/workflow_answer/evaluate_workflow_answer.py backend/evaluation/workflow_answer/query_inputs/seed_cases.jsonl --report-dir backend/evaluation/workflow_answer/reports/manual_run
```

如果要启用现有 LLM 基础设施参与语义维度评分：

```bash
python backend/evaluation/workflow_answer/evaluate_workflow_answer.py backend/evaluation/workflow_answer/query_inputs/seed_cases.jsonl --use-llm --report-dir backend/evaluation/workflow_answer/reports/manual_run
```

## 约定

- retrieval 只评 `Knowledge` 证据，不纳入长期记忆检索
- `core` 不作为 retrieval 证据来源竞争项，只在 answer 评测里参与上下文判断
- `like/dislike` 是辅助信号，不是真值标签
- `workflow_answer/` 只保留 topic-specific 配置与实现
- 规则层与 LLM 层并行产出维度结果
- 模型失败回退发生在 `finalize_impl.py -> graders/finalize_layer/`
- 最终权重计算、hard cap 和综合分统一由 finalize 侧负责
