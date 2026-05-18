# Test Data Generate

## 1. 这部分现在讲什么

`notes/intent/test_data_generate/` 现在主要讲：

> `intent / request understanding` 这条线的数据是怎么一批一批长出来的，以及每一批分别服务什么目标。

当前最重要的不是单个 campaign，而是 **三批数据生成史**。

## 2. 三批数据生成史

### 第一批：为调 rule 层生成

目标：

- 调 rule 命中质量
- 打边界样本
- 建立 rule supervision
- 识别命中质量问题与设计问题

这一批数据更关注：

- 对抗样本
- twin pairs
- near miss
- mixed intent
- clarify / challenge / follow_up 边界

它服务的是：

- `rule quality`
- `rule design`

### 第二批：为小模型 / SFT 生成

目标：

- 形成结构化训练标签
- 把 `main_intent / modifiers / task` 这些理解结果沉淀成训练资产
- 为后续小模型接管中层理解做准备

这一批数据更关注：

- `gold / heldout / export`
- 训练切分
- 标注口径一致性
- baseline 对齐

它服务的是：

- `SFT` / 小模型训练准备
- teacher / baseline 交接

### 第三批：为 V2 迁移生成

目标：

- 服务 `V2` 新 schema
- 服务 `V2 auto`
- 服务新的 signal taxonomy
- 服务 `evidence / resolver` 边界重构

这一批数据更关注：

- `V1 vs V2 auto`
- `quality gate`
- `signal migration`
- `resolved diff`
- `context_fact / ambiguity_state / clarify_candidate`

它服务的是：

- `V2 migration`
- 新 understanding 口径
- 新规则/数据线治理

## 3. 数据边界说明

这部分一定要和别的目录分清。

### `backend_test/intent/test_data/`

这是本地测试数据源。

里面放的是：

- 测试样本源
- campaign 输入
- gold / silver / heldout

### `evaluation/intent/`

这是消费测试数据后的产物区。

里面放的是：

- `V2 auto annotations`
- `quality gate`
- `diff report`
- training exports
- migration reports

### 这两个不能混

原则是：

- `test_data` 是源
- `evaluation` 是结果
- 自动标注和报告不回写源数据

## 4. 这部分推荐怎么读

如果你想理解项目的数据演进，建议按这个顺序：

1. [campaigns_and_results.md](./campaigns_and_results.md)
2. 看三批数据分别服务什么目标
3. 再回到对应的 `evaluation/intent/` 产物理解当前状态

## 5. 这部分和面试讲解的关系

这部分对项目讲解很重要，因为它能说明：

1. 这条线不是拍脑袋改规则
2. 数据、规则、评估、迁移是一起演进的
3. 为什么后来会从 rule 调优，走到 SFT 准备，再走到 V2 迁移

## 6. 一句话总结

`test_data_generate/` 现在不是“放几份生成脚本说明”的目录，而是：

> 用来讲清楚这条 understanding 线的数据是如何从 rule 调优资产，发展到 SFT 资产，再发展到 V2 迁移资产的专题区。
