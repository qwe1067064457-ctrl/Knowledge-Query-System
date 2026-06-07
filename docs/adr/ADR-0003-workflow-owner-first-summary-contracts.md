# ADR-0003: Owner-First Summary Contracts For Review And Evidence

## Status

Accepted

## Context

workflow 在 `retrieval -> challenge -> review` 这条主链上，最容易漂移的部分不是对象本身，而是：

- summary 由谁拥有
- 高频状态应该从哪里读
- 外部 dict 导出应信任谁

如果没有正式规则，后续很容易重新出现：

- 从 `review_findings` 倒推 review summary
- 从中间 fallback summary dict 反向定义 owner 状态
- 先把 owner 字段落成 dict，再从 dict 读回来
- 不同 accessor、`summary_view()`、`to_dict()` 之间语义不一致

## Decision

正式采用 **owner-first summary contract** 原则：

1. summary 应属于 bundle / result owner 本身
2. 高频状态读取优先走：
   - owner accessor
   - `summary_view()`
3. 外部 dict 导出也应优先反映 owner 状态，而不是继续携带过期 fallback 值

### 当前正式 owner

- `ReviewBundle`
  - final review contract owner
- `EvidenceBundle`
  - retrieval summary owner
- `EvidenceAssessmentResult`
  - evidence coverage / follow-up retrieval / target coverage owner

### 当前正式规则

- `ExecutionPayload` 只做 bundle 聚合与转发，不重新拥有 summary 语义
- `ReviewBundle.summary_view()` 优先消费 `EvidenceAssessmentResult.summary_view()`
- `ReviewBundle` 的高频 accessor 应与 `summary_view()` 保持同一套 owner-first 语义
- `ReviewBundle.summary_obj()` / `to_dict()["review_summary"]` 也应优先导出 owner 状态
- `EvidenceBundle.summary_view()` 应优先直接从 retrieval owner 字段生成
- `EvidenceBundle.summary_obj()` 是 `summary_view()` 的兼容导出层，而不是独立 owner

## Consequences

### Positive

- summary ownership 更清楚，后续维护不必反复猜“这个状态以谁为准”
- 高频读取逻辑更一致，减少 accessor / view / dict 导出之间的语义分叉
- `retrieval -> challenge -> review` seam 更容易继续扩展，而不是退回到散 dict

### Negative / Tradeoffs

- 需要对布尔字段、计数字段、fallback 逻辑保持更严格的 owner-first 审计
- 某些兼容层看起来会比直接返回旧 dict 更啰嗦

## Revisit Signals

出现下面情况时，可以考虑重开这个 ADR：

- owner-first 规则明显导致大量样板代码而收益不足
- 外部消费链正式切换为完全 typed，summary dict 导出不再重要
- 新的 summary owner 结构比当前 bundle/result 拥有更清晰的长期收益
