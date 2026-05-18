# Intent Notes README

`notes/intent/` 是 `intent` 这条工作线的主主题目录。

这一层应尽量只保留相对稳定的理解，包括：

- `input -> evidence -> resolved -> control` 四层链路
- 当前 intent 架构与边界
- confidence 与评估口径
- 当前小模型 SFT 讨论的最佳交接入口

阶段推进中的文档、还在变化的过程材料，不要继续堆在这一层，而是放到 `../working/intent/`。

## 主入口文档

### `intent_project_info.md`

适合先读它的场景：

- 想快速理解 `intent` 全貌
- 想看四层结构
- 想看当前架构边界
- 想看长期 TODO 方向

### `intent_testing_and_evaluation.md`

适合先读它的场景：

- 想看当前测试分层
- 想理解 `overall / per_batch / rule_stats`
- 想看当前数据与评估边界

### `intent_rule_confidence.md`

适合先读它的场景：

- 想理解规则侧 confidence 的含义
- 想看 support bonus、conflict、context adjustment 怎么工作

### `intent_sft_delivery.md`

适合先读它的场景：

- 想从一个新对话快速接手当前 SFT 阶段
- 想看当前 rules、query inputs、gold、supervision、held-out、export 之间的关系

### `multisignal_dev_heldout_backfill_plan_20260517.md`

适合先读它的场景：

- 想看为什么当前 multi-signal SFT 的 `dev/heldout` 还不能稳定评估
- 想看 6 个边界 signal 目前各缺多少覆盖
- 想看应该优先从哪些 `query_inputs / silver` 池提样
- 想看 `heldout_v3` 为什么需要新建而不是回改 `frozen_heldout_v2`

## 参考子目录

### `signal_info/`

这是细粒度 signal 参考区。

适合回答这类问题：

- 某个 signal 属于哪一层
- 某个字段是 matched rule、business signal、dependency signal，还是 candidate result
- `candidate_intents`、`signal_buckets`、`rule_confidence` 的区别是什么

推荐先看：

1. `signal_info/README.md`
2. `signal_info/evidence_signal_info/README.md`

### `test_data_generate/`

这是 intent 测试数据生成与 campaign 使用区。

推荐先看：

1. `test_data_generate/README.md`
2. `test_data_generate/campaigns_and_results.md`

## 已移出的 working 文档

下面这些文档仍然重要，但更适合当作过渡材料看待：

- `../working/intent/rule_tuning.md`
- `../working/intent/rule_supervision.md`
- `../working/intent/rule_lessons.md`
- `../working/intent/sft_preparation.md`

## 推荐阅读顺序

如果是第一次进入 `intent` 主题，建议：

1. `intent_project_info.md`
2. `intent_testing_and_evaluation.md`
3. `intent_rule_confidence.md`
4. `intent_sft_delivery.md`
5. 只有当前话题已经进入调优、监督、经验复盘或过渡性 SFT 准备时，再进入 `../working/intent/`

## 当前定位

当前的 `intent` 主题，最好理解为：

- 一个结构化 intent pipeline，而不只是分类器
- 一个正在为未来小模型接入做准备的规则与评估系统
- 一个以 `notes/intent/` 为稳定入口、以 `notes/working/intent/` 为过渡层的专题工作区
