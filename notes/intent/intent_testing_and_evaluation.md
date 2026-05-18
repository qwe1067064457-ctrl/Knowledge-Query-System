# Intent Testing and Evaluation

## 1. 这篇文档讲什么

这篇文档只讲当前这条线怎么测、怎么比、怎么判断质量。

它主要回答：

1. 我们现在到底在测什么
2. `V1` 和 `V2 auto` 怎么对比
3. 什么叫命中质量问题
4. 什么叫设计问题
5. 自动质量闸门在看什么

## 2. 当前评估分层

当前我们不再把所有质量问题混成一个“总分”，而是分层评估。

### 2.1 命中质量问题

这是最传统的一层，主要看单条 rule：

- 该命中没命中
- 不该命中却命中了

常用指标：

- precision
- recall
- f1
- required hit

### 2.2 设计问题

这是当前更重要的一层，主要看：

- signal 设计是否干净
- bucket 是否合理
- resolver 收敛是否合理
- control 是否吃到了错误的上游结构

也就是说：

- `rule quality != evidence design quality`
- `rule quality != resolver quality`

## 3. 当前主要评估对象

### 3.1 `evidence` 层

现在重点看：

- `intent signals`
- `task signals`
- `context_fact signals`
- `safety signals`

关注点包括：

1. 新 signal 有没有异常暴增
2. 旧 signal 该退场的有没有退场
3. bucket 里有没有异常迁移

### 3.2 `resolved` 层

重点字段：

- `main_intent`
- `modifiers`
- `task.complexity`
- `task.shape`
- `task.topology`
- `context_dependency`
- `ambiguity_state`

### 3.3 `control` 层

当前 control 还处于兼容迁移态，但仍然要看：

- `route`
- `mode` / `handling_mode`
- 关键 capability 开关

## 4. 当前主要评估方式

### 4.1 label diff

`V1 vs V2 auto` 差异报告不是只看最终标签，也不是只看 signal，而是两层一起看：

1. `Evidence Diff`
- signal 变了什么
- bucket 迁移了什么
- 哪些 signal 被新增/收缩/退场

2. `Resolved / Control Diff`
- `main_intent`
- `modifiers`
- `complexity`
- `shape`
- `topology`
- `route`
- `mode`

### 4.2 quality gate

当前质量闸门至少看四类：

1. `完整性`
- 字段是否齐全
- schema 是否完整

2. `信号迁移质量`
- 新信号是否异常暴增
- 旧信号是否正确退场
- bucket 是否发生异常迁移

3. `收敛结果质量`
- 标签结果是否自洽

4. `分布稳定性`
- `overall`
- `per-batch`
- `per-dataset`

## 5. 为什么不能只看 per-rule 指标

如果只看单条 rule 的 precision / recall，会漏掉三个大问题：

1. signal 虽然命中对了，但职责设计脏了
2. resolver 虽然吃到的 signal 没明显错，但收敛错了
3. 某一批数据整体漂了，但单条 rule 看起来没坏

所以：

- per-rule 指标是必要的
- 但不够

## 6. 当前报告和产物的边界

### `backend_test/intent/test_data/`

这是源测试数据区。

放的是：

- gold
- silver
- heldout
- campaign seeds

### `evaluation/intent/`

这是评估与导出产物区。

放的是：

- `V2 auto annotations`
- `V1 vs V2 auto diff report`
- `quality gate`
- training exports
- migration reports

原则：

- `test_data` 是源
- `evaluation` 是消费源后产生的结果
- 不回写源数据

## 7. 当前最重要的两个框架

### 7.1 rule 层问题二分法

当前所有问题，优先按这两个方向拆：

1. `命中质量问题`
2. `设计问题`

### 7.2 quality 层级

当前质量体系建议按四层理解：

1. `rule hit quality`
2. `signal migration quality`
3. `resolved convergence quality`
4. `distribution stability`

## 8. 当前最常看的指标

### 全局

- `resolved_main_intent_accuracy`
- `control_route_accuracy`
- `control_mode_accuracy`

### 分批次

重点看：

- `follow_up`
- `challenge`
- `clarify`
- `mixed_intent`
- `compare`
- `verify`

### 分规则

重点看：

- `ask_source`
- `challenge`
- `soft_doubt`
- `follow_up`
- `scope_question`
- `unsupported`

## 9. 当前一句话总结

现在这条线的 testing / evaluation 已经不再只是“看规则命中率”，而是：

> 同时检查 signal 迁移、resolver 收敛、control 分流和全局分布稳定性的分层质量体系。
