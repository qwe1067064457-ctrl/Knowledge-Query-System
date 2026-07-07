# Frontend Required Backend Interface Checklist

这份清单用于对齐 `QA Runner V2` 当前前端已依赖、后端应稳定提供的接口 contract。

目标不是提前把后端包装成完整 runtime，而是先明确：

1. 前端现在已经在用、后端必须稳定提供什么
2. 为了把决策链路做完整，后端下一步应该补什么
3. 哪些 runtime 接口现在还不用急着做

---

## 1. 当前必须稳定提供

### 1.1 `POST /api/chat`

| 接口 | 必需字段 / 事件 | 当前状态 | 前端依赖点 | 优先级 | 备注 |
| --- | --- | --- | --- | --- | --- |
| `POST /api/chat` | SSE 输出 `intent_analysis` | 已接入 | Agent 决策链路可视化 | P0 | 当前在 `AgentManager.astream()` 中于 `classify_intent(...)` 后发出 |
| `POST /api/chat` | SSE 输出 `workflow_plan` | 已接入 | Workflow plan 可视化 | P0 | 当前在 `build_workflow_plan(...)` 后发出 |
| `POST /api/chat` | SSE 输出 `execution_update` | 已接入 | Route payload summary 可视化 | P0 | 当前仅输出 `stage=route_payload_ready` |
| `POST /api/chat` | SSE 输出 `retrieval` | 已存在 | Retrieval steps 展示 | P0 | 保持现有事件结构稳定 |
| `POST /api/chat` | SSE 输出 `tool_start` / `tool_end` | 已存在 | Tool 调用展示 | P0 | 保持现有事件结构稳定 |
| `POST /api/chat` | SSE 输出 `token` / `done` / `error` | 已存在 | 主聊天流输出 | P0 | 继续由 API 层原样透传 |

推荐最小事件结构：

`intent_analysis`

```json
{
  "type": "intent_analysis",
  "input": {},
  "evidence": {},
  "resolved": {},
  "control": {}
}
```

`workflow_plan`

```json
{
  "type": "workflow_plan",
  "plan": {}
}
```

`execution_update`

```json
{
  "type": "execution_update",
  "stage": "route_payload_ready",
  "payload": {}
}
```

状态说明：

- API 层当前已经是 `agent_manager.astream() -> 原样转 SSE`
- 不建议为了这批事件去大改 [backend/api/chat.py](/C:/Users/HUAWEI/PycharmProjects/Skill-First-Hybrid-RAG/backend/api/chat.py)
- 当前主 contract 应落在 [backend/graph/agent.py](/C:/Users/HUAWEI/PycharmProjects/Skill-First-Hybrid-RAG/backend/graph/agent.py) 和 [backend/graph/serializers/frontend_trace.py](/C:/Users/HUAWEI/PycharmProjects/Skill-First-Hybrid-RAG/backend/graph/serializers/frontend_trace.py)

### 1.2 Sessions 接口

| 接口 | 必需字段 | 当前状态 | 前端依赖点 | 优先级 | 备注 |
| --- | --- | --- | --- | --- | --- |
| `GET /api/sessions` | `id`, `title`, `created_at`, `updated_at`, `message_count`, `active_group_id`, `allowed_group_ids` | 已具备 | 会话列表、按组过滤 | P0 | 当前返回值已包含组信息 |
| `POST /api/sessions` | 同上 | 已具备 | 新建会话后立即入列表 | P0 | 当前 `create_default_session(...)` 已返回组信息 |
| `PUT /api/sessions/{session_id}` | 标题更新后的 session 结构 | 基本具备 | 重命名会话 | P1 | 当前返回 `build_session_record(...)`，不是列表摘要结构 |
| `DELETE /api/sessions/{session_id}` | `{ "ok": true }` | 已具备 | 删除会话 | P1 | 当前足够 |
| `GET /api/sessions/{session_id}/history` | 历史消息结构 | 已具备基础消息 | 历史聊天回放 | P0 | 当前还未持久化 trace 字段 |

推荐列表返回最小结构：

```json
{
  "id": "xxx",
  "title": "新会话",
  "created_at": 0,
  "updated_at": 0,
  "message_count": 0,
  "active_group_id": "general",
  "allowed_group_ids": ["general"]
}
```

状态说明：

- [backend/api/sessions.py](/C:/Users/HUAWEI/PycharmProjects/Skill-First-Hybrid-RAG/backend/api/sessions.py) 已在 `GET /sessions` 返回 `active_group_id` 和 `allowed_group_ids`
- [backend/api/session_views.py](/C:/Users/HUAWEI/PycharmProjects/Skill-First-Hybrid-RAG/backend/api/session_views.py) 的 `create_default_session(...)` 已对齐这两个字段
- `history` 当前只稳定保留 `content / tool_calls / retrieval_steps`

### 1.3 Groups 接口

| 接口 | 必需字段 | 当前状态 | 前端依赖点 | 优先级 | 备注 |
| --- | --- | --- | --- | --- | --- |
| `GET /api/groups` | `id`, `name`, `status`, `default_agent_id`, `knowledge`, `memory_policy` | 已具备 | 组选择下拉、按组管理会话 | P0 | `GroupRecord.to_dict()` 已包含这些字段 |

状态说明：

- [backend/api/groups.py](/C:/Users/HUAWEI/PycharmProjects/Skill-First-Hybrid-RAG/backend/api/groups.py) 当前直接返回 group service 输出
- [backend/group_management/models.py](/C:/Users/HUAWEI/PycharmProjects/Skill-First-Hybrid-RAG/backend/group_management/models.py) 中 `GroupRecord.to_dict()` 已包含：
  - `id`
  - `name`
  - `status`
  - `default_agent_id`
  - `knowledge`
  - `memory_policy`

### 1.4 Files 接口

| 接口 | 必需字段 | 当前状态 | 前端依赖点 | 优先级 | 备注 |
| --- | --- | --- | --- | --- | --- |
| `GET /api/files?path=...` | `path`, `content` | 已具备 | Inspector 文件检查面板 | P0 | 当前有白名单路径限制 |
| `POST /api/files` | `ok`, `path`, `blocked` | 已具备 | Inspector 文件编辑/保存 | P1 | `knowledge/` 路径保存后会发文件事件 |

状态说明：

- [backend/api/files.py](/C:/Users/HUAWEI/PycharmProjects/Skill-First-Hybrid-RAG/backend/api/files.py) 当前不是 memory runtime 接口
- 它更像是 Inspector 的文件读写入口
- 前端不应把它当成“运行时记忆结构”的正式来源

### 1.5 Knowledge Index 接口

| 接口 | 必需字段 | 当前状态 | 前端依赖点 | 优先级 | 备注 |
| --- | --- | --- | --- | --- | --- |
| `GET /api/knowledge/index/status` | index status payload | 已具备 | 知识索引维护状态展示 | P1 | 当前直接返回 `knowledge_indexer.status().to_dict()` |
| `POST /api/knowledge/index/rebuild` | `{ "accepted": true }` | 已具备 | 手动触发重建 | P1 | 当前为异步触发 |

---

## 2. 下一步应该补

### 2.1 Session History 持久化 Trace

| 接口 | 应补字段 | 当前状态 | 价值 | 优先级 | 备注 |
| --- | --- | --- | --- | --- | --- |
| `GET /api/sessions/{session_id}/history` | `intent_trace`, `workflow_trace`, `execution_events` | 未补 | 刷新后保留决策链路 | P0 | 这是前端链路从“仅实时可见”走向“可回放”的关键 |

建议消息结构后续扩成：

```json
{
  "role": "assistant",
  "content": "...",
  "tool_calls": [],
  "retrieval_steps": [],
  "intent_trace": {},
  "workflow_trace": {},
  "execution_events": []
}
```

当前判断：

- [backend/api/chat.py](/C:/Users/HUAWEI/PycharmProjects/Skill-First-Hybrid-RAG/backend/api/chat.py) 的持久化逻辑只收集：
  - `content`
  - `tool_calls`
  - `retrieval_steps`
- 这意味着前端刷新后，目前看不到旧消息对应的 `intent_analysis / workflow_plan / execution_update`

### 2.2 Sessions 支持按 Group 查询

| 接口 | 应补能力 | 当前状态 | 价值 | 优先级 | 备注 |
| --- | --- | --- | --- | --- | --- |
| `GET /api/sessions?group_id=law` | 服务端按组过滤 | 未补 | 减少前端全量拉取后本地过滤 | P1 | 当前前端仍可先用本地过滤兜底 |

当前判断：

- [backend/api/sessions.py](/C:/Users/HUAWEI/PycharmProjects/Skill-First-Hybrid-RAG/backend/api/sessions.py) 当前 `GET /sessions` 没有 `group_id` 查询参数
- 前端现在是“先拉全量 sessions，再按 `active_group_id` 本地过滤”

### 2.3 Runtime Memory 正式入口

| 接口 | 建议新增 | 当前状态 | 价值 | 优先级 | 备注 |
| --- | --- | --- | --- | --- | --- |
| Runtime Memory APIs | `GET /api/runtime/memory/overview` | 未实现 | 前端正确展示当前 memory 总览 | P1 | 不建议让前端猜文件 |
| Runtime Memory APIs | `GET /api/runtime/memory/core` | 未实现 | 展示 core memory | P1 | 应独立于 Inspector |
| Runtime Memory APIs | `GET /api/runtime/memory/policies` | 未实现 | 展示 group memory policy | P1 | 应与 group 视图衔接 |
| Runtime Context APIs | `GET /api/runtime/context/assembly-latest` | 未实现 | 展示最新 context assembly 结果 | P1 | 适合接 context injection 说明 |

这些接口适合承接前端展示：

- core memory
- group memory policy
- memory injection summary
- context assembly result

---

## 3. 现在还不用急着做

### 3.1 完整 Workflow Runtime 事件

当前不要急着做这些事件：

- `unit_started`
- `unit_running`
- `unit_completed`
- `unit_failed`
- `pause_requested`
- `resume`
- `human_approval_required`

原因：

当前真实执行链路仍更接近：

```text
build_workflow_plan
-> dispatcher.dispatch(plan).run(...)
-> 一次性得到 execution_payload
```

它还不是一个真正的流式 runtime。

### 3.2 Run 级控制接口

当前不要急着做这些接口：

- `POST /api/workflow/runs/{run_id}/pause`
- `POST /api/workflow/runs/{run_id}/resume`
- `POST /api/workflow/runs/{run_id}/approve`

原因：

- 这些接口属于下一阶段 runtime 控制面
- 如果当前先做，很容易让后端 contract 先假装存在能力，再被内部实现反过来牵着走

---

## 4. 建议执行顺序

1. 稳住 `POST /api/chat` 的 3 个前端 trace 事件 contract
2. 给 `session history` 持久化 `intent_trace / workflow_trace / execution_events`
3. 补 `GET /api/sessions?group_id=...`
4. 设计独立的 runtime memory / context 读取接口
5. 最后再进入真正的 workflow runtime 设计

---

## 5. 一句话结论

如果只看“当前前端能正常工作并展示 Agent 决策链路”，后端最关键的是：

1. `POST /api/chat` 稳定输出 `intent_analysis / workflow_plan / execution_update`
2. `GET/POST /api/sessions` 稳定带上 `active_group_id / allowed_group_ids`
3. `GET /api/groups` 稳定返回组列表
4. 后续给 `session history` 持久化 `intent_trace / workflow_trace / execution_events`

当前代码状态看，1、2、3 基本已经成形，最值得继续推进的是第 4 点。
