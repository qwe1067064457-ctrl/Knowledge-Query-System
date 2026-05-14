# Intent 信号说明

## 1. 目录目标

这个目录用于沉淀 `intent` 模块里的细粒度信号说明。

它比 `intent_project_info.md` 更细，重点不是讲整体架构，而是讲：

- 每个 signal 是什么意思
- 每个字段属于哪一层
- 规则命中如何变成业务信号
- 候选分数和规则置信度有什么区别
- 哪些信号容易混淆，应该如何区分

## 2. 当前文档

### [evidence_signal_info](./evidence_signal_info/README.md)

详细说明 `evidence` 层。

重点包括：

- 规则命中层
- 业务信号层
- 解释约束层
- 候选结果层
- `signal_buckets`
- `dependency_signals`
- `ContextSignals`
- `unsupported_signals`
- `CandidateIntent.score`
- 易混淆信号边界

