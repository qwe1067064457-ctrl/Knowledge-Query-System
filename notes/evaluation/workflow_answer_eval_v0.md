# Workflow + Answer Evaluation v0

## 目标

第一阶段只评：

- `Knowledge retrieval`
- `final answer`

评测复用 `backend/observability/` 共享证据层，不重造事实层。

## 核心产物

- 统一 `case`
- 统一 `result`
- 维度标签
- 综合分
- bad case 原因标签
- 人工复核路由

## 关键约束

- retrieval 只看 `Knowledge`
- `core` 只在 answer 评测里参与上下文判断
- `like/dislike` 只是辅助信号
- 第一阶段只消费摘要字段

## 当前实现形态

- 主题目录：`backend/evaluation/workflow_answer/`
- 主脚本：`backend/evaluation/workflow_answer/evaluate_workflow_answer.py`
- 执行骨架：`backend/evaluation/core/runner.py`
- topic config：`backend/evaluation/workflow_answer/topic_config.py`
- 规则入口：`backend/evaluation/workflow_answer/rule_impl.py`
- 模型入口：`backend/evaluation/workflow_answer/model_impl.py`
- finalize 入口：`backend/evaluation/workflow_answer/finalize_impl.py`
- 输出：`results.jsonl`、`summary.json`、`report.md`
