# Handoff: Frontend Refactor for Intent Evidence Workflow

## Summary

前端需要从“聊天 + 检索轨迹 + 工具调用”的旧工作台，升级为能展示当前 Agent 主链的可观测界面：

```text
User Query
  -> Intent Layer
     -> raw signals
     -> TypedEvidence
     -> Evidence Quality Gate
     -> optional LLM Adjudication
     -> ResolvedIntent
     -> ControlSignal
  -> Workflow Policy
  -> Workflow Route
  -> Retrieval / Memory / Execution
  -> Final Answer
```

这次前端改造的重点不是做一个更花的聊天窗口，而是让用户能看懂：系统为什么这样路由、为什么需要/不需要 LLM judge、为什么走 qa/orchestrated/chat/reject，以及后续执行链用了哪些证据。

## Current Frontend State

当前前端是 Next.js + React，主要入口：

```text
frontend/src/lib/api.ts
frontend/src/lib/store.tsx
frontend/src/components/chat/ChatPanel.tsx
frontend/src/components/chat/ChatMessage.tsx
frontend/src/components/chat/RetrievalCard.tsx
frontend/src/components/chat/ThoughtChain.tsx
frontend/src/components/editor/InspectorPanel.tsx
```

当前 UI 已支持：

```text
聊天流式输出
retrieval SSE event 展示
tool_start / tool_end 展示
session history
token stats
knowledge index status
```

当前 UI 不支持：

```text
intent analysis 展示
typed evidence 展示
quality gate case_level 展示
LLM adjudication 展示
resolved intent / control signal 展示
workflow plan / execution payload 展示
orchestrated unit graph 展示
memory/context block 展示
```

## Backend Event Gap

当前 `backend/api/chat.py` 会把 `agent_manager.astream()` 的事件原样转成 SSE，但 `backend/graph/agent.py` 目前主要向前端流：

```text
token
done
retrieval
tool_start / tool_end
new_response
error
```

意图识别和 workflow 信息目前更多写到 LangSmith observability，并没有稳定推给前端。

前端改造最好配合后端新增这些 SSE event：

```text
intent_analysis
workflow_plan
execution_update
answer_assembly
context_assembly
memory_event
```

如果短期不改后端，前端只能先做组件和类型占位，等事件接入后再展示真实数据。

## Target Information Architecture

聊天消息里的 assistant bubble 建议分成四个可折叠区域：

```text
1. Decision Trace
   展示 intent / gate / control / workflow route

2. Evidence Board
   展示 typed evidence、accepted/downgraded/rejected、conflicts、ambiguities

3. Execution Trace
   展示 workflow route、orchestrated unit graph、unit status、retrieval quality

4. Answer
   展示最终自然语言回答
```

首屏不要把所有 JSON 倒出来。默认展示高层状态，展开后看细节。

## Recommended UI Layout

### Top Status Strip

在每条 assistant message 顶部展示一条状态带：

```text
Route: qa / orchestrated / chat / reject
Handling: normal / clarify / challenge / scope_info / unsupported
Gate: auto_resolve / auto_resolve_with_warnings / blocked_by_missing_prerequisite / requires_adjudication / guard_required
LLM Judge: skipped / used
```

颜色建议：

```text
auto_resolve: green / ocean
auto_resolve_with_warnings: amber
requires_adjudication: orange
blocked_by_missing_prerequisite: blue
guard_required: red
```

### Decision Trace Card

展示最终执行决策：

```text
main_intent
task.complexity
task.shape
task.topology
context_dependency
control.route
control.handling_mode
control.capabilities
decision.reason
```

这张卡面向用户解释“系统准备怎么处理”。

### Evidence Board

按三列展示：

```text
Accepted
Downgraded
Rejected
```

每条 evidence 展示：

```text
signal
value
source
criticality
score
threshold
margin
calibration_quality
missing_prerequisites
rationale
```

source 建议显示为角色化名称：

```text
surface_trigger -> 哨兵
small_model -> 证人
context_state -> 上下文事实
llm_adjudication -> 裁判
```

不要把 downgraded 翻译成“错误”。它是 warning / weak evidence。

### Gate Summary

单独展示：

```text
case_level
case_reason
conflicts
ambiguities
missing_prerequisites
```

核心文案：

```text
Gate 判断这个 case 能不能自动收敛。
只有 requires_adjudication 才需要 LLM judge。
blocked_by_missing_prerequisite 直接 clarify。
guard_required 直接 reject。
```

### LLM Adjudication Card

只有 `adjudication_result` 存在时展示。

展示：

```text
accepted_evidence
corrected_evidence
rejected_evidence
clarified_ambiguity_type
fallback_recommendation
reason
```

UI 文案必须避免暗示 LLM 是最终 resolver。正确表述：

```text
LLM 只裁决争议 evidence，最终仍由 resolver/control_signal 映射执行协议。
```

### Workflow Trace

展示 workflow 层：

```text
route
action
policy_flags
enabled_powers
planning_mode
fallback_used
fallback_reason
```

如果是 orchestrated，展示 execution graph：

```text
unit_id
goal
capability
depends_on
state
output_slot
retrieval_quality_status
```

可以先做列表，后续再做 DAG 可视化。

### Memory / Context Trace

后续可展示：

```text
core memory injected
retrieved daily_log
retrieved domain_case
context blocks
compaction summary
token budget
```

注意核心文案：

```text
core memory 默认注入。
daily_log / domain_case 按需检索。
memory hit 应尽量保留历史上下文 anchor。
```

## Type Additions

建议在 `frontend/src/lib/api.ts` 增加这些类型。字段保持宽松，避免后端演进导致前端崩。

```ts
export type EvidenceSource =
  | "surface_trigger"
  | "small_model"
  | "context_state"
  | "retrieval_trace"
  | "human"
  | "llm_adjudication";

export type CaseLevelOutcome =
  | "auto_resolve"
  | "auto_resolve_with_warnings"
  | "blocked_by_missing_prerequisite"
  | "requires_adjudication"
  | "guard_required";

export type SignalCriticality =
  | "route"
  | "task_shape"
  | "context_dependency"
  | "safety"
  | "modifier"
  | "diagnostic";

export type TypedEvidence = {
  signal: string;
  value: unknown;
  source: EvidenceSource;
  score: number | null;
  threshold: number | null;
  margin: number | null;
  calibration_quality: "good" | "weak" | "unknown";
  prerequisites: string[];
  missing_prerequisites: string[];
  criticality: SignalCriticality;
  rationale: string;
};

export type EvidenceQualityReport = {
  accepted_evidence: TypedEvidence[];
  downgraded_evidence: TypedEvidence[];
  rejected_evidence: TypedEvidence[];
  conflicts: string[];
  ambiguities: string[];
  missing_prerequisites: string[];
  case_level: CaseLevelOutcome;
  case_reason: string;
};

export type AdjudicationResult = {
  accepted_evidence: TypedEvidence[];
  corrected_evidence: TypedEvidence[];
  rejected_evidence: TypedEvidence[];
  clarified_ambiguity_type: string;
  fallback_recommendation: CaseLevelOutcome;
  reason: string;
};

export type IntentTrace = {
  typed_evidence: TypedEvidence[];
  quality_report: EvidenceQualityReport | null;
  adjudication_result: AdjudicationResult | null;
  resolved: Record<string, unknown> | null;
  control: Record<string, unknown> | null;
};
```

`Message` 建议扩展：

```ts
type Message = {
  id: string;
  role: "user" | "assistant";
  content: string;
  toolCalls: ToolCall[];
  retrievalSteps: RetrievalStep[];
  intentTrace?: IntentTrace;
  workflowTrace?: WorkflowTrace;
  executionEvents?: ExecutionEvent[];
};
```

## Store Changes

`frontend/src/lib/store.tsx` 需要处理新 SSE event：

```text
intent_analysis:
  normalizeIntentTrace(data)
  patch active assistant message.intentTrace

workflow_plan:
  normalizeWorkflowTrace(data)
  patch active assistant message.workflowTrace

execution_update:
  append to active assistant message.executionEvents

context_assembly:
  patch context trace if needed

memory_event:
  append memory event if needed
```

历史消息接口目前只保存：

```text
content
tool_calls
retrieval_steps
```

如果要刷新后仍保留链路 trace，需要后端 session entry 增加：

```text
intent_trace
workflow_trace
execution_events
context_trace
memory_trace
```

短期可以只支持实时展示，不持久化。

## Component Plan

新增组件建议：

```text
frontend/src/components/trace/DecisionTraceCard.tsx
frontend/src/components/trace/EvidenceBoard.tsx
frontend/src/components/trace/GateSummary.tsx
frontend/src/components/trace/AdjudicationCard.tsx
frontend/src/components/trace/WorkflowTraceCard.tsx
frontend/src/components/trace/ExecutionUnitList.tsx
frontend/src/components/trace/TracePill.tsx
```

修改组件：

```text
ChatMessage.tsx
  接收 intentTrace / workflowTrace / executionEvents
  assistant 消息顶部展示 Decision Trace

ChatPanel.tsx
  保持布局，但标题从“实时对话与检索轨迹”改成“Agent 决策链路”

RetrievalCard.tsx
  保留，用作 Execution Trace 的一个子区域

ThoughtChain.tsx
  保留，用作 tool trace

store.tsx
  增加 event parsing 和 message trace state

api.ts
  增加 trace 类型和 normalizer
```

## Backend Contract Suggestion

建议 `agent_manager.astream()` 在 `classify_intent()` 后立即 yield：

```python
yield {
    "type": "intent_analysis",
    "input": intent_analysis.input.to_dict(),
    "evidence": intent_analysis.evidence.to_dict(),
    "resolved": intent_analysis.resolved.to_dict(),
    "control": intent_analysis.control.to_dict(),
}
```

在 `build_workflow_plan()` 后 yield：

```python
yield {
    "type": "workflow_plan",
    "plan": workflow_plan.to_dict(),
}
```

在 execution payload 生成后 yield：

```python
yield {
    "type": "execution_update",
    "payload": execution_payload.to_dict(),
}
```

注意不要把 LangSmith 当成前端数据源。LangSmith 是观测后端，前端需要稳定的 SSE/API contract。

## UX Copy Rules

避免这些词：

```text
模型判断正确
规则判断错误
LLM 最终决定
rejected = 拒绝用户
```

推荐这些词：

```text
accepted = 已采信
downgraded = 弱证据 / 仅作提示
rejected = 未用于本次决策
requires_adjudication = 需要裁决
guard_required = 触发安全/能力边界
blocked_by_missing_prerequisite = 缺少必要上下文
```

## Visual Direction

保持现有暖色、纸张感、rounded panel 风格，不要改成普通后台表格。

建议把主链做成横向 trace：

```text
Evidence
  -> Gate
  -> Adjudication?
  -> Resolver
  -> Control
  -> Workflow
```

每个节点用状态色：

```text
green: auto resolved
amber: warning
orange: adjudication
blue: clarify
red: guard/reject
gray: skipped
```

移动端优先变成纵向 timeline。

## Acceptance Criteria

前端完成后，至少满足：

```text
1. 用户能在 assistant message 顶部看到 route、handling_mode、case_level。
2. 用户能展开看到 accepted/downgraded/rejected evidence。
3. requires_adjudication case 能显示 LLM adjudication 是否发生，以及裁决了什么。
4. blocked_by_missing_prerequisite 显示为 clarify，不显示成 LLM failure。
5. guard_required 显示为安全/能力边界，不显示成普通错误。
6. orchestrated route 能看到 execution units 或至少看到 workflow payload summary。
7. 检索轨迹和工具调用继续正常展示。
8. 如果后端暂时没有 trace event，UI 不报错，只隐藏 trace 区域。
9. 刷新历史消息时，若后端没有持久化 trace，不影响正常聊天记录展示。
```

## Implementation Order

建议顺序：

```text
1. api.ts 增加 trace 类型和 normalizer。
2. store.tsx 扩展 Message，支持 intent_analysis / workflow_plan / execution_update event。
3. 新增 trace 基础组件：TracePill、GateSummary、DecisionTraceCard。
4. 改 ChatMessage，把 trace card 放到 assistant message 顶部。
5. 新增 EvidenceBoard，展示 evidence 三列。
6. 新增 WorkflowTraceCard，先列表展示 route/payload/unit。
7. 后端补 SSE event contract。
8. 做一个 fake event fixture，便于前端无后端时调试。
9. 最后再考虑 DAG 可视化。
```

## Risks

主要风险：

```text
1. 后端 trace contract 还不稳定，前端要做宽松解析。
2. evidence 数量可能很多，默认必须折叠。
3. rejected evidence 容易被用户误解为“拒绝请求”，文案要谨慎。
4. LLM adjudication 容易被误解为最终决策者，UI 要强调它只裁决 evidence。
5. 如果 session history 不持久化 trace，刷新后 trace 消失，这是 v1 可接受限制，但需要产品上说明。
```

## One-Line Goal

把前端从“聊天窗口”升级成“Agent 决策链路可视化工作台”：用户不仅看到答案，还能看到系统如何从 evidence 收敛到 workflow route。
