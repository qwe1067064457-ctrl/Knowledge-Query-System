# Intent 测试、评估与训练准备说明

## 1. 当前文档的作用

这份文档只回答三件事：

1. 当前 `intent` 线怎么测
2. 当前 `V2` 数据与导出在哪
3. 当前 SFT baseline 和训练准备做到哪

它不再把重点放在旧的 `V1` 兼容解释上。

## 2. 当前评估主线

当前评估仍按四层结构理解：

```text
input -> evidence -> resolved -> control
```

但需要注意：

- 当前 `V2` 重点已经放在 `evidence + resolved`
- `control` 还没有完成 `V2` 重构

所以如果当前任务是：

- 继续推进 understanding
- 准备小模型 SFT
- 判断数据是否可训练

应优先观察：

- `evidence`
- `resolved`
- 训练导出与 baseline 数据

## 3. 当前真实存在的重要脚本与目录

### 3.1 评估与迁移脚本

- [evaluation/intent/evaluate_intent_rules.py](/C:/Users/HUAWEI/PycharmProjects/Skill-First-Hybrid-RAG/evaluation/intent/evaluate_intent_rules.py)
- [evaluation/intent/export_intent_training_set.py](/C:/Users/HUAWEI/PycharmProjects/Skill-First-Hybrid-RAG/evaluation/intent/export_intent_training_set.py)
- [evaluation/intent/v2_migration.py](/C:/Users/HUAWEI/PycharmProjects/Skill-First-Hybrid-RAG/evaluation/intent/v2_migration.py)
- [evaluation/intent/compare_v1_v2_auto_labels.py](/C:/Users/HUAWEI/PycharmProjects/Skill-First-Hybrid-RAG/evaluation/intent/compare_v1_v2_auto_labels.py)
- [evaluation/intent/quality_gate_v2_auto.py](/C:/Users/HUAWEI/PycharmProjects/Skill-First-Hybrid-RAG/evaluation/intent/quality_gate_v2_auto.py)
- [evaluation/intent/auto_uplift_silver.py](/C:/Users/HUAWEI/PycharmProjects/Skill-First-Hybrid-RAG/evaluation/intent/auto_uplift_silver.py)

### 3.2 训练导出

当前导出目录：

- [evaluation/intent/exports/](/C:/Users/HUAWEI/PycharmProjects/Skill-First-Hybrid-RAG/evaluation/intent/exports)

当前明确存在的 `V2` 导出：

- [evaluation/intent/exports/intent_training_v2.jsonl](/C:/Users/HUAWEI/PycharmProjects/Skill-First-Hybrid-RAG/evaluation/intent/exports/intent_training_v2.jsonl)

其它 `v1 / v3 / v4 / v5 / v6 / v7` 文件仍保留，但不应自动当成“当前正式 V2 口径”。

### 3.3 SFT 与 baseline 准备

- [backend/intent/sft/](/C:/Users/HUAWEI/PycharmProjects/Skill-First-Hybrid-RAG/backend/intent/sft)
- [evaluation/intent/multisignal_sft/](/C:/Users/HUAWEI/PycharmProjects/Skill-First-Hybrid-RAG/evaluation/intent/multisignal_sft)
- [evaluation/intent/prepare_macbert_baseline_data.py](/C:/Users/HUAWEI/PycharmProjects/Skill-First-Hybrid-RAG/evaluation/intent/prepare_macbert_baseline_data.py)
- [evaluation/intent/run_macbert_baseline.py](/C:/Users/HUAWEI/PycharmProjects/Skill-First-Hybrid-RAG/evaluation/intent/run_macbert_baseline.py)

## 4. 当前 baseline 状态

当前这条线已经进入：

- 小模型 SFT baseline 已完成

这意味着：

- 当前不是“能不能开始 baseline”的阶段
- 而是“baseline 之后怎么继续优化”的阶段

因此现在更值得看的不是：

- 要不要继续补更多 rule

而是：

- 当前 `V2` 导出是否足够支撑下一轮训练
- 哪些样本还需要 review
- 哪些标签最值得优先优化

## 5. 当前数据层次怎么理解

当前更推荐按下面几层理解：

1. `query_inputs`
- 原始 query 池、种子 query、benchmark 输入

2. `reports`
- 评估运行结果、campaign 报告、summary

3. `exports`
- 可训练导出

4. `multisignal_sft`
- 与多信号 SFT、dev/heldout backfill 相关的专项资产

5. `backend/intent/sft`
- 训练与数据读取侧的代码

## 6. 当前测试与回归

当前 `intent` 线的主要黑盒测试仍在：

- [backend_test/intent/](/C:/Users/HUAWEI/PycharmProjects/Skill-First-Hybrid-RAG/backend_test/intent)

重点保护：

- classifier 行为
- resolver 收敛
- control 映射
- rule confidence
- 导出与迁移脚本

如果当前你是在继续推进 understanding，而不是改 workflow，优先保证：

- `backend_test/intent` 稳定通过

## 7. 当前最重要的评估边界

### 7.1 已经相对稳定的

- `evidence v2` 主结构
- `resolved` 的 task 轴
- `V2` 导出基础链路
- baseline 数据准备入口

### 7.2 还未完全收口的

- `control v2`
- 真正的 workflow 执行口径
- 训练后如何把 understanding 结果安全接到 execution

所以当前训练与评估的推荐策略是：

- 先把小模型用于 `understanding`
- 不要一上来就让它承担完整 execution 决策

## 8. 当前文档怎么配合使用

如果你当前任务是：

### 看整体架构

先看：

- [intent_project_info.md](/C:/Users/HUAWEI/PycharmProjects/Skill-First-Hybrid-RAG/notes/intent/intent_project_info.md)

### 看信号与字段

先看：

- [signal_info/README.md](/C:/Users/HUAWEI/PycharmProjects/Skill-First-Hybrid-RAG/notes/intent/signal_info/README.md)

### 看 SFT 准备与数据生成

先看：

- [test_data_generate/README.md](/C:/Users/HUAWEI/PycharmProjects/Skill-First-Hybrid-RAG/notes/intent/test_data_generate/README.md)

### 看历史多信号补数背景

只当参考看：

- [multisignal_dev_heldout_backfill_plan_20260517.md](/C:/Users/HUAWEI/PycharmProjects/Skill-First-Hybrid-RAG/notes/intent/multisignal_dev_heldout_backfill_plan_20260517.md)
