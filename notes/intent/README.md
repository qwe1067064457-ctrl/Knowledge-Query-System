# Intent Notes README

`notes/intent/` 是当前 `intent / request understanding` 工作线的稳定说明入口。

这层文档的目标不是记录所有阶段性讨论，而是回答下面几件事：

- 当前 understanding 主链是什么
- `evidence + resolver` 的 `V2` 已迁移到什么程度
- 当前评估、训练准备与 SFT baseline 在哪里
- 哪些文档仍是当前事实来源，哪些只是历史参考

阶段推进中的材料、一次性推演、尚未收口的思路，优先继续放在
`../working/intent/`，不要回灌到这一层。

## 当前结论

当前 `intent` 线最准确的定位是：

- 它已经不只是传统的 intent classification
- 它更接近 `request understanding`
- 正式 understanding 主骨架是：
  - `intent`
  - `task`
  - `context`
  - `safety`

当前主链仍然按四层理解：

```text
input -> evidence -> resolved -> control
```

其中：

- `evidence + resolver` 的 `V2` 迁移已经基本完成
- `control` 仍处于旧语义过渡态，尚未完成 `V2` 收口

## 推荐阅读顺序

1. [intent_project_info.md](/C:/Users/HUAWEI/PycharmProjects/Skill-First-Hybrid-RAG/notes/intent/intent_project_info.md)
   - 先看当前架构边界、V2 定位、未完成项
2. [intent_testing_and_evaluation.md](/C:/Users/HUAWEI/PycharmProjects/Skill-First-Hybrid-RAG/notes/intent/intent_testing_and_evaluation.md)
   - 先看当前评估、训练导出、baseline 与数据状态
3. [intent_rule_confidence.md](/C:/Users/HUAWEI/PycharmProjects/Skill-First-Hybrid-RAG/notes/intent/intent_rule_confidence.md)
   - 先看规则证据可信度评审器到底是什么
4. [architecture/README.md](/C:/Users/HUAWEI/PycharmProjects/Skill-First-Hybrid-RAG/notes/intent/architecture/README.md)
   - 先看主架构、信号分类与 rule-lite 的稳定设计
5. [signal_info/README.md](/C:/Users/HUAWEI/PycharmProjects/Skill-First-Hybrid-RAG/notes/intent/signal_info/README.md)
   - 先看 `evidence v2` 的正式语义分类与字段职责
6. [control/README.md](/C:/Users/HUAWEI/PycharmProjects/Skill-First-Hybrid-RAG/notes/intent/control/README.md)
   - 先看当前 `control v2` 的边界、contract 与迁移检查项
7. [migrations/README.md](/C:/Users/HUAWEI/PycharmProjects/Skill-First-Hybrid-RAG/notes/intent/migrations/README.md)
   - 先看 intent 体系升级、旧字段退场和兼容出口收口
8. [test_data_generate/README.md](/C:/Users/HUAWEI/PycharmProjects/Skill-First-Hybrid-RAG/notes/intent/test_data_generate/README.md)
   - 先看当前测试数据、SFT 准备数据与 baseline 相关入口

## 当前主入口文档

### [intent_project_info.md](/C:/Users/HUAWEI/PycharmProjects/Skill-First-Hybrid-RAG/notes/intent/intent_project_info.md)

适合在这些场景先读：

- 想快速理解 `intent` 线现在做到哪
- 想知道 `rule-lite + model-centric understanding` 在当前仓库里意味着什么
- 想确认 `evidence/resolver` 和 `control/workflow` 的边界

### [intent_testing_and_evaluation.md](/C:/Users/HUAWEI/PycharmProjects/Skill-First-Hybrid-RAG/notes/intent/intent_testing_and_evaluation.md)

适合在这些场景先读：

- 想看当前测试、评估、导出、baseline 准备的真实入口
- 想知道 `V2` 训练导出和 baseline 相关目录在哪
- 想区分哪些数据是训练资产，哪些只是评估或历史数据

### [intent_rule_confidence.md](/C:/Users/HUAWEI/PycharmProjects/Skill-First-Hybrid-RAG/notes/intent/intent_rule_confidence.md)

适合在这些场景先读：

- 想确认 `rule_confidence` 到底是不是概率
- 想知道它如何判断当前 rule evidence 靠不靠谱

## 子目录入口

### [signal_info/](/C:/Users/HUAWEI/PycharmProjects/Skill-First-Hybrid-RAG/notes/intent/signal_info)

这个目录专门讲 `evidence` 里的正式信号体系。

当前以 `V2` 为准，只保留一套正式语义分类：

- `intent`
- `task`
- `context`
- `safety`

它更适合回答：

- 某个信号属于哪一类
- `signal_buckets`、`candidate_intents`、`task_candidates`、`context_signals`、`unsupported_signals` 的边界是什么
- 哪些旧字段已经退出正式 schema

推荐先看：

1. [signal_info/README.md](/C:/Users/HUAWEI/PycharmProjects/Skill-First-Hybrid-RAG/notes/intent/signal_info/README.md)
2. [signal_info/evidence_signal_info/README.md](/C:/Users/HUAWEI/PycharmProjects/Skill-First-Hybrid-RAG/notes/intent/signal_info/evidence_signal_info/README.md)

### [architecture/](/C:/Users/HUAWEI/PycharmProjects/Skill-First-Hybrid-RAG/notes/intent/architecture)

这个目录专门放 intent / request understanding 主线里的稳定架构说明。

更适合回答：

- understanding 主架构现在怎么分层
- 信号分类和 rule-lite 的当前定位是什么
- 哪些设计已经算主线事实，不只是阶段性想法

推荐先看：

1. [architecture/README.md](/C:/Users/HUAWEI/PycharmProjects/Skill-First-Hybrid-RAG/notes/intent/architecture/README.md)
2. [architecture/intent_understanding_architecture.md](/C:/Users/HUAWEI/PycharmProjects/Skill-First-Hybrid-RAG/notes/intent/architecture/intent_understanding_architecture.md)
3. [architecture/intent_signal_taxonomy.md](/C:/Users/HUAWEI/PycharmProjects/Skill-First-Hybrid-RAG/notes/intent/architecture/intent_signal_taxonomy.md)

### [control/](/C:/Users/HUAWEI/PycharmProjects/Skill-First-Hybrid-RAG/notes/intent/control)

这个目录专门放 understanding 输出如何进入执行控制层的文档。

更适合回答：

- `control v2` 的正式边界是什么
- `route / handling_mode / capabilities / trace` 如何分工
- 当前 control 迁移和兼容字段退出怎么做

推荐先看：

1. [control/README.md](/C:/Users/HUAWEI/PycharmProjects/Skill-First-Hybrid-RAG/notes/intent/control/README.md)
2. [control/control_signal_v2.md](/C:/Users/HUAWEI/PycharmProjects/Skill-First-Hybrid-RAG/notes/intent/control/control_signal_v2.md)
3. [control/control_contract.md](/C:/Users/HUAWEI/PycharmProjects/Skill-First-Hybrid-RAG/notes/intent/control/control_contract.md)

### [migrations/](/C:/Users/HUAWEI/PycharmProjects/Skill-First-Hybrid-RAG/notes/intent/migrations)

这个目录专门放 intent 体系迁移、兼容出口收口和旧字段退场说明。

推荐先看：

1. [migrations/README.md](/C:/Users/HUAWEI/PycharmProjects/Skill-First-Hybrid-RAG/notes/intent/migrations/README.md)
2. [migrations/intent_v2_migration.md](/C:/Users/HUAWEI/PycharmProjects/Skill-First-Hybrid-RAG/notes/intent/migrations/intent_v2_migration.md)

### [test_data_generate/](/C:/Users/HUAWEI/PycharmProjects/Skill-First-Hybrid-RAG/notes/intent/test_data_generate)

这个目录专门讲测试数据、query 输入、训练导出与 SFT 准备。

它更适合回答：

- 现在有哪些 query 输入和 campaign 入口
- `intent_training_v2.jsonl` 是怎么来的
- MacBERT baseline 数据如何准备
- 哪些文档是历史多信号补数据计划，哪些是当前仍可执行的准备说明

推荐先看：

1. [test_data_generate/README.md](/C:/Users/HUAWEI/PycharmProjects/Skill-First-Hybrid-RAG/notes/intent/test_data_generate/README.md)
2. [test_data_generate/sft_preparation_data_generation_lessons.md](/C:/Users/HUAWEI/PycharmProjects/Skill-First-Hybrid-RAG/notes/intent/test_data_generate/sft_preparation_data_generation_lessons.md)

## 当前真实存在的重要目录与脚本

### 训练导出与评估

- [evaluation/intent/exports/intent_training_v2.jsonl](/C:/Users/HUAWEI/PycharmProjects/Skill-First-Hybrid-RAG/evaluation/intent/exports/intent_training_v2.jsonl)
- [evaluation/intent/export_intent_training_set.py](/C:/Users/HUAWEI/PycharmProjects/Skill-First-Hybrid-RAG/evaluation/intent/export_intent_training_set.py)
- [evaluation/intent/evaluate_intent_rules.py](/C:/Users/HUAWEI/PycharmProjects/Skill-First-Hybrid-RAG/evaluation/intent/evaluate_intent_rules.py)
- [evaluation/intent/v2_migration.py](/C:/Users/HUAWEI/PycharmProjects/Skill-First-Hybrid-RAG/evaluation/intent/v2_migration.py)
- [evaluation/intent/quality_gate_v2_auto.py](/C:/Users/HUAWEI/PycharmProjects/Skill-First-Hybrid-RAG/evaluation/intent/quality_gate_v2_auto.py)

### SFT 与 baseline 准备

- [backend/intent/sft/](/C:/Users/HUAWEI/PycharmProjects/Skill-First-Hybrid-RAG/backend/intent/sft)
- [evaluation/intent/multisignal_sft/](/C:/Users/HUAWEI/PycharmProjects/Skill-First-Hybrid-RAG/evaluation/intent/multisignal_sft)
- [evaluation/intent/prepare_macbert_baseline_data.py](/C:/Users/HUAWEI/PycharmProjects/Skill-First-Hybrid-RAG/evaluation/intent/prepare_macbert_baseline_data.py)
- [evaluation/intent/run_macbert_baseline.py](/C:/Users/HUAWEI/PycharmProjects/Skill-First-Hybrid-RAG/evaluation/intent/run_macbert_baseline.py)

### 当前状态说明

- 当前分支上，小模型 SFT baseline 已经是既有事实
- 但这层 README 不记录单次训练结果细节
- 训练结果、下一轮优化建议，应优先回到 `evaluation/intent/` 和对应报告中查看

## 历史材料

下面这类文档仍保留，但不再视为当前唯一真相：

- [history/multisignal_dev_heldout_backfill_plan_20260517.md](/C:/Users/HUAWEI/PycharmProjects/Skill-First-Hybrid-RAG/notes/intent/history/multisignal_dev_heldout_backfill_plan_20260517.md)

它们的作用更接近：

- 历史阶段记录
- 旧问题背景
- 为什么会走到现在这套 `V2` 结构

如果当前任务是继续推进 `V2`，优先相信上面的主入口文档，不要优先回读历史计划。
