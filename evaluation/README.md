# Evaluation

`evaluation/` 存放评估相关的脚本、输入集、导出数据和结果报告。

当前以 `intent/` 为主，是 intent 规则评估、小模型训练准备和基线实验的工作区。

现在新增 `workflow_answer/` 主题，用于第一阶段：

- `Knowledge retrieval` 质量评测
- `final answer` 质量评测
- 统一 case / result schema
- 离线回放与线上抽样后的异步评测

## 阅读顺序

1. `evaluation/intent/README.md`
2. `evaluation/workflow_answer/README.md`
3. `evaluation/intent/query_inputs/README.md`
4. `evaluation/workflow_answer/query_inputs/README.md`
5. `evaluation/intent/reports/README.md`
6. `evaluation/intent/exports/README.md`

## 放置原则

- 评估脚本：放在对应主题目录下，例如 `evaluation/intent/*.py`
- 评估输入：放在 `query_inputs/`
- 评估结果报告：放在 `reports/`
- 导出训练集或 baseline 数据：放在 `exports/`
- 人工审核材料：保留在主题目录根部，便于和评估脚本一起维护

## 当前状态

- 现在 `evaluation/` 继续按主题拆分
- `intent/` 负责 intent 方向
- `workflow_answer/` 负责 Workflow + Retrieval + Answer 方向
- 如果后续出现 compaction、memory preservation 等独立专题，再按 `evaluation/<topic>/` 继续展开
