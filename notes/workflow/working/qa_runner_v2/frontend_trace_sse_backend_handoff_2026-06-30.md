# Frontend Trace SSE Backend Handoff

这份交接文档对应 2026-06-30 的前后端对齐任务。

目标不是立刻把后端重构成完整 Workflow Runtime，而是先把前端已经接好的
`intent_analysis` / `workflow_plan` / `execution_update` 三类可观测事件稳定推给 SSE。

## 1. 先说结论

当前后端最该做的是：

1. 先把内部决策对象稳定暴露给前端。
2. 不要马上把 route runner 重构成完整事件流工作流引擎。
3. 先让前端能看见主链，再讨论 `run_id / unit_state / pause / resume / human approval`。

一句话收口：

`v1 = 可观测事件输出`

不是：

`v1 = 完整 runtime 状态机`

## 2. 当前真实结构

当前链路已经是：

```text
backend/api/chat.py
  -> agent_manager.astream()
  -> 原样转成 SSE
```

这意味着：

- API 层当前不是主改点。
- 主要改动在 [backend/graph/agent.py](/C:/Users/HUAWEI/PycharmProjects/Skill-First-Hybrid-RAG/backend/graph/agent.py)。
- `chat.py` 只需要继续把事件原样透传，并在后续决定是否持久化 trace 字段。

当前 `astream()` 里已经存在这些关键阶段：

```text
prepare messages
-> classify_intent(...)
-> build_workflow_plan(...)
-> workflow_dispatcher.dispatch(plan).run(...)
-> model answer / agent answer / knowledge orchestrator
```

并且关键对象已经具备 `to_dict()`：

- `IntentAnalysis`
- `WorkflowPlan`
- `ExecutionPayload`

所以第一阶段不需要为“对象怎么序列化”去改业务主链，只需要加一层
`frontend trace serializer` 做字段裁剪和稳定出口。

## 3. 第一阶段范围

第一阶段只做下面 3 个 SSE 事件：

1. `intent_analysis`
2. `workflow_plan`
3. `execution_update`

推荐事件顺序：

```text
intent_analysis
-> workflow_plan
-> execution_update(stage=route_payload_ready)
-> retrieval / tool_start / tool_end / token / done
```

其中：

- `execution_update` 当前先只承接一次 `route_payload_ready`
- 不承诺 `unit_started / unit_running / unit_completed / unit_failed`
- 不承诺 `pause_requested / human_approval_required / resume`

## 4. 为什么现在不要直接做完整 runtime

当前 runner 真实形态更像：

```text
build_workflow_plan
  -> dispatcher.dispatch(plan).run(...)
  -> 一次性返回 execution_payload
```

所以它当前更接近：

- 执行前准备
- route 级执行收口
- answer 前载荷生成

而不是：

- 带 `run_id` 的长生命周期 workflow runtime
- 带 unit 级状态流转的事件总线
- 带暂停恢复和人工确认的执行状态机

正确节奏应该是：

```text
v1: 打通 intent_analysis / workflow_plan / execution_update
v2: 给 workflow run 增加 run_id + unit states
v3: runner 从 run() 升级成 stream()/astream()
v4: 支持 pause/resume/human approval
```

## 5. 建议新增文件

建议新增：

- [backend/graph/serializers/frontend_trace.py](/C:/Users/HUAWEI/PycharmProjects/Skill-First-Hybrid-RAG/backend/graph/serializers/frontend_trace.py)

建议提供 3 个函数：

```python
serialize_intent_analysis(intent_analysis) -> dict[str, Any]
serialize_workflow_plan(workflow_plan) -> dict[str, Any]
serialize_execution_payload(execution_payload, *, stage: str) -> dict[str, Any]
```

这里的职责边界是：

- 给前端稳定字段
- 屏蔽后续内部对象细节变化
- 避免 [backend/graph/agent.py](/C:/Users/HUAWEI/PycharmProjects/Skill-First-Hybrid-RAG/backend/graph/agent.py) 越来越胖

不要在 serializer 里：

- 新造 runtime 逻辑
- 补不存在的业务状态
- 重新解释 intent / workflow 主链

## 6. 推荐事件 payload

### 6.1 `intent_analysis`

推荐最小结构：

```python
{
    "type": "intent_analysis",
    "input": intent_analysis.input.to_dict(),
    "evidence": intent_analysis.evidence.to_dict(),
    "resolved": intent_analysis.resolved.to_dict(),
    "control": intent_analysis.control.to_dict(),
}
```

说明：

- 前端现在已经能消费 `evidence.quality_report`、`evidence.adjudication_result`
- 不需要再单独拼一份“前端专用语义”
- 优先复用 `IntentAnalysis.to_dict()` 的已有稳定结构

### 6.2 `workflow_plan`

推荐最小结构：

```python
{
    "type": "workflow_plan",
    "plan": workflow_plan.to_dict(),
}
```

说明：

- 前端会关心 `route`、`handling_mode`、`policy_flags`、`enabled_powers`、`trace`
- `WorkflowPlan.to_dict()` 已经足够支撑第一阶段可视化

### 6.3 `execution_update`

推荐第一阶段结构：

```python
{
    "type": "execution_update",
    "stage": "route_payload_ready",
    "payload": execution_payload.to_dict(),
}
```

说明：

- 这里表达的是“route 级 payload 已经收口完成”
- 不是“runtime 内每个 unit 的实时状态变化”
- 前端会把它展示成 workflow payload summary 和 execution units 概览

## 7. `AgentManager.astream()` 建议插入点

建议只在 3 个位置加 `yield`。

### 7.1 classify 后

```python
intent_analysis = classify_intent(...)
yield serialize_intent_analysis_event(intent_analysis)
```

### 7.2 build_workflow_plan 后

```python
workflow_plan = build_workflow_plan(...)
yield serialize_workflow_plan_event(workflow_plan)
```

### 7.3 execution_payload 生成后

```python
execution_payload = self.workflow_dispatcher.dispatch(workflow_plan).run(...)
yield serialize_execution_payload_event(
    execution_payload,
    stage="route_payload_ready",
)
```

这里要注意两个边界：

1. 这些事件要出现在最终 answer token 之前。
2. 不要影响现有 `retrieval` / `tool_start` / `tool_end` / `token` / `done` 的输出顺序。

## 8. API 层当前建议

[backend/api/chat.py](/C:/Users/HUAWEI/PycharmProjects/Skill-First-Hybrid-RAG/backend/api/chat.py)
当前已经会把 `agent_manager.astream()` 事件原样转成 SSE。

第一阶段建议：

- 不大改 API 层
- 继续原样透传新事件
- 暂时不强推 session history trace 持久化

但是可以顺手加一个很小的 TODO 注释：

- 当前 history 持久化只存 `content / tool_calls / retrieval_steps`
- 后续如要刷新保留 trace，需要再扩 `intent_trace / workflow_trace / execution_events`

## 9. 测试建议

第一阶段要补黑盒测试。

优先新增：

- `backend_test/api/test_chat_trace_sse.py`
- 或 `backend_test/graph/test_agent_trace_stream.py`

推荐以 `pytest` 写黑盒测试，用临时目录，不污染真实数据。

### 9.1 至少覆盖的正例

1. 当 `agent_manager.astream()` 进入正常主链时，SSE 顺序里包含：
   - `intent_analysis`
   - `workflow_plan`
   - `execution_update`
   - `done`
2. `intent_analysis` 事件里至少有：
   - `input`
   - `evidence`
   - `resolved`
   - `control`
3. `workflow_plan` 事件里至少有：
   - `plan.route`
   - `plan.handling_mode`
4. `execution_update` 事件里至少有：
   - `stage == "route_payload_ready"`
   - `payload.route`
   - `payload.action`

### 9.2 至少覆盖的反例

1. 当前 route runner 不是 runtime stream 时，不要伪造：
   - `unit_started`
   - `unit_completed`
   - `pause_requested`
2. serializer 输入缺少预期对象时：
   - 返回结构化最小字段
   - 或显式失败
   - 但不要静默造假字段

### 9.3 测试风格建议

- 用 monkeypatch/stub 固定 `classify_intent`、`build_workflow_plan`、`dispatcher.run()` 输出
- 重点测事件顺序和关键字段存在
- 不把测试耦合到真实 LLM / 真正工具执行

## 10. 第二阶段不在本次范围

本次不要承诺下面这些：

- `run_id`
- `unit state`
- `unit_started / unit_running / unit_completed / unit_failed`
- `pause / resume`
- `human approval required`
- 真正的 workflow runtime 事件总线

这些属于第二阶段及以后。

## 11. 推荐落地顺序

按这个顺序做最稳：

1. 新增 `backend/graph/serializers/frontend_trace.py`
2. 在 `AgentManager.astream()` 分类后 yield `intent_analysis`
3. 在 `build_workflow_plan()` 后 yield `workflow_plan`
4. 在 `execution_payload` 生成后 yield `execution_update`
5. 补 `pytest` 黑盒测试，验证 SSE 事件顺序和字段存在
6. 再考虑 session history 是否持久化 trace
7. 最后才设计真正的 Workflow Runtime

## 12. 对后端实现者的提醒

实现时请始终记住这句话：

前端现在需要的是“稳定看到后端已经做出的决策对象”，不是“后端提前假装自己已经有完整 runtime 状态机”。

先把真实对象稳定暴露出来，再往 runtime 演进，会更干净，也更不容易把 contract 做坏。
