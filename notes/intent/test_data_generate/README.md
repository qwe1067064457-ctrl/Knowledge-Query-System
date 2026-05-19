# Intent 测试数据与训练准备说明

## 1. 当前目录的定位

这个目录专门沉淀：

- 测试数据生成
- query 输入资产
- 训练导出准备
- baseline 前后的数据理解

它不负责解释整个四层架构，也不负责定义 control/workflow。

## 2. 当前最重要的事实

当前这条线已经进入：

- `V2 understanding` 训练与迭代阶段

并且：

- 小模型 SFT baseline 已经完成

所以这份目录当前更重要的作用，不是回答“能不能开始 baseline”，而是回答：

- 当前有哪些训练准备资产
- 当前哪类数据能继续用
- 旧的多信号 backfill 计划应如何理解

## 3. 当前真实入口

### 3.1 query 输入

优先看：

- [evaluation/intent/query_inputs/README.md](/C:/Users/HUAWEI/PycharmProjects/Skill-First-Hybrid-RAG/evaluation/intent/query_inputs/README.md)

### 3.2 导出与评估

优先看：

- [evaluation/intent/exports/README.md](/C:/Users/HUAWEI/PycharmProjects/Skill-First-Hybrid-RAG/evaluation/intent/exports/README.md)
- [evaluation/intent/reports/README.md](/C:/Users/HUAWEI/PycharmProjects/Skill-First-Hybrid-RAG/evaluation/intent/reports/README.md)

### 3.3 当前 `V2` 导出

当前明确存在的训练导出：

- [evaluation/intent/exports/intent_training_v2.jsonl](/C:/Users/HUAWEI/PycharmProjects/Skill-First-Hybrid-RAG/evaluation/intent/exports/intent_training_v2.jsonl)

### 3.4 baseline 相关

- [evaluation/intent/prepare_macbert_baseline_data.py](/C:/Users/HUAWEI/PycharmProjects/Skill-First-Hybrid-RAG/evaluation/intent/prepare_macbert_baseline_data.py)
- [evaluation/intent/run_macbert_baseline.py](/C:/Users/HUAWEI/PycharmProjects/Skill-First-Hybrid-RAG/evaluation/intent/run_macbert_baseline.py)
- [backend/intent/sft/](/C:/Users/HUAWEI/PycharmProjects/Skill-First-Hybrid-RAG/backend/intent/sft)
- [evaluation/intent/multisignal_sft/](/C:/Users/HUAWEI/PycharmProjects/Skill-First-Hybrid-RAG/evaluation/intent/multisignal_sft)

## 4. 当前数据层次怎么理解

当前更推荐按下面几层理解：

1. `query_inputs`
- 原始 query 池、seed、benchmark 输入

2. `campaign / generated drafts`
- 测试或扩展生成中间产物

3. `exports`
- 可直接被训练或 baseline 消费的导出

4. `reports`
- 评估与数据质量观察结果

5. `multisignal_sft`
- 多信号训练专项资产

这比旧的“只围绕四层草稿生产”更贴近现在的实际工作流。

## 5. 当前推荐阅读顺序

1. [sft_preparation_data_generation_lessons.md](/C:/Users/HUAWEI/PycharmProjects/Skill-First-Hybrid-RAG/notes/intent/test_data_generate/sft_preparation_data_generation_lessons.md)
   - 看数据生产方法论
2. [campaigns_and_results.md](/C:/Users/HUAWEI/PycharmProjects/Skill-First-Hybrid-RAG/notes/intent/test_data_generate/campaigns_and_results.md)
   - 看已有 campaign 和结果资产
3. 对应的 `evaluation/intent` 目录
   - 看当前真实脚本、导出和报告

## 6. 当前这份目录不再主推什么

当前不再建议把这个目录读成：

- 只服务旧的 `V1` 规则评估
- 只服务“从 seed 扩到 gold”的单向流程
- 只服务“baseline 尚未开始”的准备阶段

它现在更准确的角色是：

- V2 数据、baseline、后续训练迭代之间的知识连接区
