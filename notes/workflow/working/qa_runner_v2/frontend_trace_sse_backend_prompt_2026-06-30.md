# Backend Implementation Prompt

你现在接手的是 `Skill-First-Hybrid-RAG` 的后端适配任务。

项目根目录：

`C:\Users\HUAWEI\PycharmProjects\Skill-First-Hybrid-RAG`

先阅读：

- [notes/workflow/working/qa_runner_v2/frontend_trace_sse_backend_handoff_2026-06-30.md](/C:/Users/HUAWEI/PycharmProjects/Skill-First-Hybrid-RAG/notes/workflow/working/qa_runner_v2/frontend_trace_sse_backend_handoff_2026-06-30.md)
- [backend/api/chat.py](/C:/Users/HUAWEI/PycharmProjects/Skill-First-Hybrid-RAG/backend/api/chat.py)
- [backend/graph/agent.py](/C:/Users/HUAWEI/PycharmProjects/Skill-First-Hybrid-RAG/backend/graph/agent.py)

## 任务目标

第一阶段只做一件事：

把前端需要的 3 个 SSE 事件打通，让前端能可视化当前 Agent 决策链路。

要支持的事件：

1. `intent_analysis`
2. `workflow_plan`
3. `execution_update`

不要在这次任务里把系统重构成完整 Workflow Runtime。

## 已知事实

当前 API 层已经会把 `agent_manager.astream()` 里的事件原样转成 SSE。

也就是说：

- 不要大改 `backend/api/chat.py`
- 主改点在 `backend/graph/agent.py`

当前主链大致是：

```text
prepare messages
-> classify_intent(...)
-> build_workflow_plan(...)
-> workflow_dispatcher.dispatch(plan).run(...)
-> answer path
```

当前对象已有 `to_dict()`：

- `IntentAnalysis`
- `WorkflowPlan`
- `ExecutionPayload`

## 具体实现要求

### 1. 新增 serializer

新增文件：

`backend/graph/serializers/frontend_trace.py`

建议提供：

```python
serialize_intent_analysis(intent_analysis) -> dict[str, Any]
serialize_workflow_plan(workflow_plan) -> dict[str, Any]
serialize_execution_payload(execution_payload, *, stage: str) -> dict[str, Any]
```

如果你觉得更清晰，也可以提供事件级函数：

```python
serialize_intent_analysis_event(...)
serialize_workflow_plan_event(...)
serialize_execution_payload_event(...)
```

要求：

- 尽量薄包装
- 优先复用现有对象 `to_dict()`
- 不要在 serializer 里新增业务判断

### 2. 在 `AgentManager.astream()` 补 3 个事件

在 `classify_intent(...)` 之后，yield：

```python
{
    "type": "intent_analysis",
    "input": intent_analysis.input.to_dict(),
    "evidence": intent_analysis.evidence.to_dict(),
    "resolved": intent_analysis.resolved.to_dict(),
    "control": intent_analysis.control.to_dict(),
}
```

在 `build_workflow_plan(...)` 之后，yield：

```python
{
    "type": "workflow_plan",
    "plan": workflow_plan.to_dict(),
}
```

在 `execution_payload = self.workflow_dispatcher.dispatch(workflow_plan).run(...)` 之后，yield：

```python
{
    "type": "execution_update",
    "stage": "route_payload_ready",
    "payload": execution_payload.to_dict(),
}
```

### 3. 事件顺序要求

这些事件必须出现在最终 answer token 之前。

推荐顺序：

```text
intent_analysis
-> workflow_plan
-> execution_update(stage=route_payload_ready)
-> retrieval / tool_start / tool_end / token / done
```

不要破坏现有：

- `retrieval`
- `tool_start`
- `tool_end`
- `token`
- `done`

### 4. 明确本次不做

不要在这次任务里承诺或臆造：

- `run_id`
- `unit_started`
- `unit_running`
- `unit_completed`
- `unit_failed`
- `pause_requested`
- `human_approval_required`
- `resume`

原因：

当前 runner 还是 `run() -> 一次性返回 execution_payload`，还不是事件流式 runtime。

### 5. 测试要求

使用 `pytest` 写黑盒测试，文件名必须是 `test_*.py`。

建议新增测试文件：

`backend_test/api/test_chat_trace_sse.py`

或：

`backend_test/graph/test_agent_trace_stream.py`

测试约束：

- 使用临时目录
- 不污染真实数据
- 每个职责至少 1 个正例 + 1 个反例

至少验证：

1. 正例：
   - 事件顺序里存在 `intent_analysis -> workflow_plan -> execution_update -> done`
   - `intent_analysis` 含 `input/evidence/resolved/control`
   - `workflow_plan.plan` 含 `route/handling_mode`
   - `execution_update.stage == "route_payload_ready"`
2. 反例：
   - 不会伪造 `unit_started/unit_completed/pause_requested`
   - serializer 不应偷偷补不存在的 runtime 状态字段

如果某些更深层 runtime 接口还不存在：

- 写 TODO
- 或 `xfail`
- 不要顺手实现第二阶段业务

## 输出要求

完成后请给出：

1. 修改了哪些文件
2. SSE 事件现在的真实字段结构
3. 测试跑了哪些命令
4. 哪些是第一阶段已完成，哪些仍留给第二阶段

## 成功标准

满足下面条件即可视为本次任务完成：

1. 前端能收到 `intent_analysis`
2. 前端能收到 `workflow_plan`
3. 前端能收到 `execution_update(stage=route_payload_ready)`
4. 现有聊天 SSE 不被破坏
5. 黑盒测试能验证关键事件顺序和字段存在

记住：

本次任务的正确方向是“先暴露真实决策对象”，不是“提前伪造完整 workflow runtime”。
