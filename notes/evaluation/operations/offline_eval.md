# Offline Eval

## 输入来源

- 手工种子 case
- 从 observability / LangSmith 导出的 trace 回放 case

## 目标

- 守回归
- 复盘 bad case
- 生成冻结 benchmark
- 比较版本前后差异

## 最小流程

1. 整理为统一 case jsonl
2. 跑 `backend/evaluation/workflow_answer/evaluate_workflow_answer.py`
3. 查看 `summary.json`
4. 优先复盘 `bad` 和 `needs_human_review`
