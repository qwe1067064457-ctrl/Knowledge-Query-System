# Intent / Request Understanding

`notes/intent/` 是当前这条线的稳定知识层，主要服务两个目标：

1. 让开发时可以快速对齐当前主设计。
2. 让项目讲解时可以清晰说明这条线的架构、演进和取舍。

这里记录的是 **当前稳定口径**，不是所有过程稿。仍在演化、仍带明显过渡性质的内容，放在 `../working/intent/`。

## 这条线现在在做什么

当前我们更准确地把它理解为：

- `request understanding`
- 而不只是传统的“意图识别”

主链路是：

```text
input -> evidence -> resolved -> control
```

当前方向是：

- `rule-lite + model-centric understanding`
- `V1 / V2` 双轨迁移
- `workflow-aware but not workflow-deciding understanding`

也就是说，这一层负责把请求理解清楚、把风险拦住、把粗分流定稳；但不再让规则层过早决定所有执行细节。

## 推荐阅读顺序

如果你是为了快速重建全局理解，建议按这个顺序读：

1. [intent_project_info.md](./intent_project_info.md)
2. [intent_understanding_architecture.md](./intent_understanding_architecture.md)
3. [intent_v2_migration.md](./intent_v2_migration.md)
4. [intent_rule_lite_strategy.md](./intent_rule_lite_strategy.md)
5. [intent_signal_taxonomy.md](./intent_signal_taxonomy.md)
6. [intent_testing_and_evaluation.md](./intent_testing_and_evaluation.md)
7. [intent_rule_confidence.md](./intent_rule_confidence.md)

## 当前稳定文档

### 1. 项目与架构

- [intent_project_info.md](./intent_project_info.md)
  - 模块定位、问题背景、当前边界和长期方向。
- [intent_understanding_architecture.md](./intent_understanding_architecture.md)
  - `input -> evidence -> resolved -> control` 四层结构与职责。

### 2. V2 迁移主线

下面几篇都属于 **V2 迁移主线**：

- [intent_v2_migration.md](./intent_v2_migration.md)
  - 为什么要做 `V2`、改了哪些边界、当前兼容态是什么。
- [intent_rule_lite_strategy.md](./intent_rule_lite_strategy.md)
  - 为什么继续 `rule-lite`，哪些继续留给 rule，哪些下放给模型或主回答层。
- [intent_signal_taxonomy.md](./intent_signal_taxonomy.md)
  - `request semantic`、`context_fact`、`task`、`safety` 的分类与命名收口。

### 3. 评估与数据

- [intent_testing_and_evaluation.md](./intent_testing_and_evaluation.md)
  - 现在怎么测、怎么做质量闸门、怎么做 `V1 vs V2 auto` 差异分析。
- [intent_rule_confidence.md](./intent_rule_confidence.md)
  - `rule confidence` 只代表规则命中层面的信心，不代表整个 understanding 主链的质量。

### 4. 数据生成专题

- [test_data_generate/README.md](./test_data_generate/README.md)
  - 重点讲 `intent` 这条线的三批数据是怎么长出来的。
- [test_data_generate/campaigns_and_results.md](./test_data_generate/campaigns_and_results.md)
  - 各批 campaign 与产物的阶段性结果。

## 子目录定位

### `signal_info/`

这是 signal 的细节索引区，适合查：

- 某个 signal 属于哪一类
- 某个 signal 之前处于什么旧命名
- 某个字段为什么会出现在 evidence 中

它是查细节的地方，不是项目主叙事入口。

### `test_data_generate/`

这是测试数据与标注数据生成史的专题区，当前重点讲三批数据：

1. 第一批：为调 `rule` 层生成的数据
2. 第二批：为 `SFT` / 小模型准备的数据
3. 第三批：为 `V2` 迁移、新 taxonomy、新 schema 准备的数据

## 和 `notes/working/intent/` 的边界

- `notes/intent/`
  - 当前稳定口径
  - 适合讲项目、对齐架构、回顾正式设计
- `notes/working/intent/`
  - 过程稿、试验稿、迁移过程中的临时协议
  - 适合查讨论过程和尚未冻结的细节

如果你发现某篇文档仍在大段讨论“是否要这样做”，那篇文档通常更应该属于 `working` 层，而不是这里。

## 当前一句话总结

现在这条线不再只是一个“意图分类器”，而是：

> 一个围绕 `request understanding` 展开的、以 `rule-lite` 为方向、以 `V1 / V2` 双轨迁移为手段、为后续小模型和主回答模型接管留接口的结构化理解系统。
