# Intent Evaluation

`evaluation/intent/` 是 intent 方向的评估与训练准备工作区。

这里的内容不是单一测试目录，而是一个围绕 intent 演进的实验与评估区，包含：

- 规则评估脚本
- 数据导出脚本
- 小模型 baseline 准备与运行脚本
- query 输入集
- 结果报告
- 人工审核与监督材料

## 目录说明

- `query_inputs/`
  - 评估输入集、种子 query、benchmark 清单
- `reports/`
  - 每次评估活动产出的总结报告和 summary json
- `exports/`
  - 导出的训练数据、baseline 数据包
- `*.py`
  - 评估、导出、baseline 运行脚本
- `rule_expectation_annotation_template.jsonl`
  - 规则监督标注模板
- `rule_expectation_review_list.md`
  - 人工审核清单
- `rule_supervision_approved_v1.jsonl`
  - 已确认可用的规则监督结果

## 推荐阅读顺序

1. `query_inputs/README.md`
2. `reports/README.md`
3. `exports/README.md`
4. 当前需要执行的脚本

## 主要脚本

- `evaluate_intent_rules.py`
  - 读取 gold 数据集并评估当前 intent 分类结果
- `generate_user_batch_v1.py`
  - 生成一批用户 query 或评估输入
- `export_intent_training_set.py`
  - 把多份 gold 或 silver 数据导出为训练集 jsonl
- `prepare_macbert_baseline_data.py`
  - 准备 MacBERT baseline 所需的数据包
- `run_macbert_baseline.py`
  - 运行 MacBERT baseline 训练或 dry-run 校验
- `auto_uplift_silver.py`
  - 对 silver 数据做自动提升或整理

## 维护约定

- 新的评估输入优先放到 `query_inputs/`
- 新的评估结果优先放到 `reports/`
- 新的训练导出或 baseline 数据包优先放到 `exports/`
- 如果只是一次性分析说明，优先补到对应子目录的 `README.md`，不要把根目录继续堆乱
