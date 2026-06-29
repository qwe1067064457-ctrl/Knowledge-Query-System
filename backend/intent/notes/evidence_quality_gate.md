# Evidence Quality Gate

## Responsibility

Evidence Quality Gate 只检查结构化 `TypedEvidence`，判断当前 case 能不能靠现有证据自动收敛。

它不读取原始 query，不做关键词命中，也不替代 resolver。规则是哨兵，小模型是证人，Gate 是法官，LLM adjudication 只在法官无法收敛时裁决争议点。

## Main Chain

```text
raw signals
  rule surface triggers
  small model probabilities
  context state
        ↓
TypedEvidence
        ↓
Evidence Quality Gate
  signal-level: accepted / downgraded / rejected
  case-level: auto_resolve / auto_resolve_with_warnings / blocked_by_missing_prerequisite / requires_adjudication / guard_required
        ↓
if requires_adjudication:
  LLM Adjudication
        ↓
Final Evidence Set
        ↓
Resolver
        ↓
ControlSignal
```

## Signal Inputs

- `source`: evidence 来自 surface trigger、小模型、上下文状态、检索轨迹、人工或 LLM 裁决。
- `margin`: 分数相对阈值的距离。
- `calibration_quality`: 当前信号的校准可信度。
- `prerequisites`: 该信号成立所需前提。
- `missing_prerequisites`: 当前缺失的前提。
- `criticality`: 信号影响 route、task shape、context dependency、safety、modifier 或 diagnostic。

## Case-Level Outcomes

- `auto_resolve`: 关键 evidence 已 accepted，无冲突、无缺前提，直接进入 resolver。
- `auto_resolve_with_warnings`: 主信号可收敛，但存在 downgraded 的非阻断证据，带 trace 进入 resolver。
- `blocked_by_missing_prerequisite`: 缺上下文前提，例如 follow-up 缺历史目标；直接映射 clarify，不走 LLM。
- `requires_adjudication`: 主信号冲突、主信号全弱、关键小模型信号不稳、或 task shape 冲突；只裁决争议 evidence。
- `guard_required`: safety / unsupported 类 evidence 命中；直接映射 reject，不走 LLM。

## Boundary

`rules/` 仍可作为 surface trigger 来源，但命中规则不等于可信语义证据。可信度由 Gate 根据结构化字段判断。

LLM adjudication 的主输入是 `typed_evidence + quality_report`；`query/context_state/history` 只能作为辅助上下文，不能让 LLM 从零重做完整 intent classification。
