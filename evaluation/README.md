# Evaluation

`evaluation/` 存放评估相关的脚本、输入集、导出数据和结果报告。

当前以 `intent/` 为主，是 intent 规则评估、小模型训练准备和基线实验的工作区。

## 阅读顺序

1. `evaluation/intent/README.md`
2. `evaluation/intent/query_inputs/README.md`
3. `evaluation/intent/reports/README.md`
4. `evaluation/intent/exports/README.md`

## 放置原则

- 评估脚本：放在对应主题目录下，例如 `evaluation/intent/*.py`
- 评估输入：放在 `query_inputs/`
- 评估结果报告：放在 `reports/`
- 导出训练集或 baseline 数据：放在 `exports/`
- 人工审核材料：保留在主题目录根部，便于和评估脚本一起维护

## 当前状态

- 现在 `evaluation/` 还比较轻，不单独拆更多层级
- 如果后续出现 retrieval、memory 等独立评估主题，再按 `evaluation/<topic>/` 继续展开
