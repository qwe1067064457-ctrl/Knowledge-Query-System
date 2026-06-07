# ADR-0002: Typed Contracts Inside, Stable Dict Contracts Outside

## Status

Accepted

## Context

workflow 的主链在收口过程中逐步引入了大量 typed contract：

- `ExecutionPayload`
- `ContextBundle`
- `PlanBundle`
- `ReviewBundle`
- `EvidenceBundle`
- `EvidenceAssessmentResult`
- `ReviewEvaluationResult`
- `RetrievalUnitResult`

但同时，外部消费链已经存在大量基于 dict shape 的兼容路径。  
如果一次性把外部消费全部改为 typed object，会显著扩大改动面，并提高回归风险。

需要一个长期稳定、可被后续维护者直接引用的原则，解释为什么 workflow 内部 typed 化推进得很深，但对外仍保留 dict contract。

## Decision

正式采用以下原则：

- workflow **内部**优先推进 typed object orchestration
- workflow **对外**继续保持 stable dict contract

这条原则适用于：

- `ExecutionPayload`
- 各类 bundle / result object
- runner / power / worker 的交界
- 对外导出的 `to_dict()` / payload dict shape

### 实施方式

1. 内部先定义 typed owner
2. 高频消费优先走：
   - accessor
   - `summary_view()`
   - owner-first 逻辑
3. 对外再通过 `to_dict()` 导出稳定 dict contract
4. 允许在兼容层保留：
   - `get(...)`
   - `__getitem__`
   但新逻辑不优先依赖这些入口

## Consequences

### Positive

- 可以持续收 workflow 内部语义，而不打断现有外部消费链
- typed contract 能先在 workflow 主链内部稳定下来
- 后续如果外部也要 typed 化，可以在已有 owner 基础上推进

### Negative / Tradeoffs

- 会存在一段时间的“双轨状态”：
  - 内部 typed
  - 外部 dict
- 需要额外维护 owner-first 与外部 dict 导出的一致性
- 兼容层逻辑如果长期不审计，容易让旧 dict 读法残留更久

## Revisit Signals

出现下面情况时，可以考虑重开这个 ADR：

- workflow 外部消费链已经基本完成 typed 化，stable dict contract 不再有明显价值
- dict compatibility 成本高于保留收益
- 内外双轨开始明显造成维护负担
