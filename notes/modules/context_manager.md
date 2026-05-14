# Context Manager 模块记录

最后整理：2026-05-12

本文件只记录 `ContextManager` 相关信息，不混入 session manager 或 memory system 的实现细节。

## 1. 模块定位

`ContextManager` 是每次 LLM 调用前的上下文阀门。

它负责把原始会话历史加工成符合 token 预算、结构合理、带必要记忆的上下文。

核心职责：

- 从 session manager 获取 transcript。
- 修复和规范化历史消息结构。
- 按完整轮次截断历史。
- 注入 memory system 提供的记忆。
- 按动态预算组装上下文。
- 必要时触发 compaction。
- compaction 前 flush 记忆。
- 把 compaction summary 写回 session。

它不负责：

- 保存原始 transcript。
- 决定长期记忆具体如何落盘。
- 做知识库文档 RAG。
- 管理前端状态。

## 2. 当前代码位置

主实现：

```text
backend/context/context_manager.py
```

配置加载：

```text
backend/context/context_policy.py
backend/context/context_policy.json
```

Prompt 管理：

```text
backend/prompts/system_prompt.md
backend/prompts/README.md
backend/graph/prompt_builder.py
```

测试目录：

```text
backend_test/context_manager/
```

## 3. 总体架构

我们讨论过上下文管理是“三层防线”，后续实现时扩展成更完整的五步管线。

当前实际管线：

```text
transcript
  -> normalize transcript
  -> limit history turns
  -> inject memories
  -> assemble context by dynamic budget
  -> compaction if needed
```

解释：

1. `normalize transcript`
   - 修复 user / assistant / tool 不成对问题。
   - 防止截断后出现孤立 assistant 或孤立 tool。

2. `limit history turns`
   - 按完整用户轮次保留最近 N 轮。
   - 默认 N = 8。

3. `inject memories`
   - core 必读注入。
   - daily_log 和 domain_case 按 query 检索注入。

4. `assemble context`
   - 按 token 预算动态组装。
   - 优先保留 core 和最近对话。
   - tool results 是最先牺牲层。

5. `compaction`
   - 预算仍超限时触发。
   - compaction 前先 flush memory。
   - LLM 生成摘要后写回 session。

## 4. ContextConfig

实现位置：

```python
backend/context/context_manager.py
```

核心配置：

```python
class ContextConfig:
    max_turns = 8

    total_tokens = 6000
    core_reserved_tokens = 300
    core_max_tokens = 600
    retrieved_target_tokens = 800
    retrieved_max_tokens = 1400
    recent_turns_target_tokens = 2000
    recent_turns_max_tokens = 3200
    tool_results_target_tokens = 400
    tool_results_max_tokens = 1000
    tool_result_max_chars = 4000

    memory_search_enabled = True
    memory_top_k = 5
    memory_time_decay_half_life = 30
    memory_use_mmr = True
    memory_mmr_lambda = 0.7

    compaction_enabled = True
    compaction_trigger_ratio = 0.9

    memory_flush_enabled = True
    memory_flush_threshold = 5400

    system_prompt_path = "prompts/system_prompt.md"
```

保留了一些 legacy 兼容字段：

```python
reserve_tokens
soft_threshold_tokens
keep_recent_tokens
image_max_dimension_px
```

## 5. context_policy.json

配置文件：

```text
backend/context/context_policy.json
```

当前结构：

```json
{
  "history": {
    "max_recent_turns": 8
  },
  "budget": {
    "total_tokens": 6000,
    "core": {
      "reserved": 300,
      "max": 600
    },
    "retrieved_memories": {
      "target": 800,
      "max": 1400
    },
    "recent_turns": {
      "target": 2000,
      "max": 3200
    },
    "tool_results": {
      "target": 400,
      "max": 1000,
      "max_chars_per_message": 4000
    }
  },
  "compaction": {
    "enabled": true,
    "trigger_ratio": 0.9,
    "keep_recent_tokens": 2000
  },
  "memory": {
    "search_enabled": true,
    "top_k": 5,
    "time_decay_half_life": 30,
    "use_mmr": true,
    "mmr_lambda": 0.7,
    "flush_enabled": true,
    "flush_threshold": 5400
  },
  "prompt": {
    "system_prompt_path": "prompts/system_prompt.md"
  }
}
```

我们讨论过是否需要配置文件，结论是：

- 需要，但第一版保持轻量。
- 配置 token 预算、memory 开关、compaction 阈值、system prompt 路径即可。
- 不做复杂平台化配置。

## 6. ContextPolicyLoader

实现位置：

```text
backend/context/context_policy.py
```

职责：

- 提供 `DEFAULT_CONTEXT_POLICY`。
- 读取 `context_policy.json`。
- 做 deep merge。
- 文件缺失或损坏时 fallback 到默认配置。

`ContextConfig.from_policy(...)` 会把 JSON policy 映射为运行时 config。

重要计算：

```text
soft_threshold_tokens = total_tokens * compaction.trigger_ratio
```

并保证不超过 `total_tokens`。

## 7. Prompt 管理

我们讨论过 prompt 要采用注入设计。

当前只做 system prompt 管理，不提前设计完整 agent prompt 平台。

相关文件：

```text
backend/prompts/system_prompt.md
backend/prompts/README.md
backend/graph/prompt_builder.py
```

当前行为：

- `prompt_builder.py` 读取 context policy 中的 `prompt.system_prompt_path`。
- 默认加载 `backend/prompts/system_prompt.md`。
- 运行时可以叠加 runtime override。

关键决策：

- system prompt 不硬编码在 agent 里。
- prompt 文件路径由 context policy 控制。
- 后续做问答 agent 层时再扩展更多 prompt 类型。

旧链路变化：

- `prompt_builder.py` 不再把 `memory/MEMORY.md` 当作 Long-term Memory 注入来源。
- memory 注入由 `ContextManager + MemorySystem` 完成。

## 8. prepare 流程

主入口：

```python
prepare(group_id, agent_id, session_id, query=None, user_id="default", llm_client=None)
```

流程：

1. 调用 `SessionManager.get_transcript(...)` 获取完整 transcript。
2. `_entries_to_messages(...)` 转成 OpenAI 风格 messages。
3. 识别最新 compaction boundary。
4. `_normalize_transcript(...)` 修复不完整轮次。
5. `_limit_history_turns(...)` 保留最近完整 N 轮。
6. `_extract_query_from_messages(...)` 获取当前查询。
7. `_inject_memories(...)` 注入 core 和 retrieved memories。
8. `_assemble_context(...)` 做动态预算裁剪。
9. 如果仍超限并且允许 compaction，则 `_trigger_compaction(...)`。
10. 返回准备好的 messages、token 信息、budget 信息、是否 compaction。

返回结构包含：

- `messages`
- `token_count`
- `needs_compaction`
- `compacted`
- `budget`

## 9. transcript 规范化

### 问题来源

如果只按消息数量或 token 截断，容易出现：

- assistant 没有对应 user。
- tool 没有对应 tool call。
- user / assistant 不配对。
- compaction 后前置系统摘要和后续消息边界混乱。

### 当前处理

`_normalize_transcript(...)` 会：

- 保留开头的 system 消息。
- 丢弃第一条 user 之前的孤立 assistant/tool。
- 按 user 开始分组。
- 避免生成不完整 turn。

`_split_turns(...)` 会把消息拆成：

- leading system
- turns

每个 turn 以 user 开始，后面可跟 assistant/tool/system。

## 10. limit_history_turns

实现：

```python
_limit_history_turns(messages)
```

语义：

- 默认保留最近 8 轮。
- “轮”不是一条消息，而是从 user 开始的一组消息。
- 截断后保持 user/assistant/tool 尽量配对。

这修复了你指出的问题：

> N 轮对话截断后，会出现 user-ai 不配对现象，这个需要处理。

当前实现是按完整 turn 截断，而不是简单数组切片。

## 11. memory 注入

实现：

```python
_inject_memories(group_id, agent_id, query, messages, user_id)
```

当前策略：

### 11.1 core 必读注入

调用：

```python
memory_sys.get_core_memories(user_id=user_id, group_id=group_id)
```

注入：

- `user_global` core。
- 当前 group 的 `user_group` core。

不注入：

- 其他用户 core。
- 其他 group 的 user_group core。
- default 用户兜底 core。

### 11.2 daily_log / domain_case 按需检索

调用：

```python
memory_sys.search(
    group_id,
    agent_id,
    query,
    include_core=False,
    include_daily_logs=True,
    include_domain_cases=True,
)
```

注意：

- `include_core=False` 是刻意设计。
- 因为 core 已经通过 `get_core_memories(...)` 必读注入。
- 避免 core 同时出现在必读块和检索块里。

### 11.3 注入位置

如果 messages 已经有 system prompt：

- memory block 插在第一条 system 后面。

如果没有 system prompt：

- memory block 插在最前面。

### 11.4 注入块标记

内部会标记：

```python
_context_block = "core_memory"
_context_block = "retrieved_memory"
```

后续预算裁剪依赖这些标记。

## 12. 预算策略

我们讨论过这些内容不是固定死切，而是思想和区间预算：

- core：固定小预算，尽量不裁。
- retrieved memories：中预算，超了优先裁低分项。
- recent turns：主预算。
- tool results：最先裁剪。

当前实现已经从“每块固定上限”升级为“动态回收”。

## 13. 动态预算回收

实现：

```python
_plan_context_budget(messages)
```

当前 block：

```text
core
retrieved_memories
recent_turns
tool_results
```

每个 block 有：

- actual：实际 token 需求。
- target：目标预算。
- max：最大可扩展预算。
- allocation：最终分配预算。

基本思想：

1. 先按目标预算分配。
2. 如果总额超出 `total_tokens`，按牺牲顺序回收。
3. 如果还有剩余 token，按优先顺序返还。

回收顺序：

```text
tool_results
retrieved_memories
recent_turns
core
```

扩展顺序：

```text
recent_turns
retrieved_memories
tool_results
core
```

含义：

- tool results 最先裁。
- core 最后裁。
- recent turns 是主预算，拿到剩余 token 的优先级最高。

## 14. assemble_context

实现：

```python
_assemble_context(messages) -> (messages, needs_compaction, budget_info)
```

流程：

1. 复制 messages，附加 `_message_index`。
2. `_trim_tool_messages(...)` 先对超长 tool result 做字符级截断。
3. `_plan_context_budget(...)` 生成动态预算。
4. `_trim_block_to_budget(...)` 裁剪 core / retrieved memory system blocks。
5. `_trim_recent_conversation(...)` 保留最近完整对话。
6. `_trim_tool_messages_to_budget(...)` 进一步裁剪或省略工具结果。
7. 计算最终 token。
8. 如果仍超过 soft threshold，则标记 `needs_compaction=True`。

`budget_info` 包含：

```text
total
used
remaining
actual
blocks
allocation
```

## 15. tool results 裁剪

你问过“tool results 裁剪是什么”。

这里指：

- 工具返回可能很长，例如检索文档、网页内容、结构化结果。
- 这些内容通常不是用户和模型的主对话。
- 在 token 压力下，它们应比 core 和 recent turns 更早被截断。

当前裁剪：

- 单条 tool message 超过 `tool_result_max_chars` 会先字符截断。
- 预算仍不足时，tool message 可能变为：

```text
[tool result omitted due to budget]
```

或追加：

```text
...[truncated]
```

## 16. compaction

实现：

```python
_trigger_compaction(...)
```

触发条件：

- `_assemble_context(...)` 后仍超过 soft threshold。
- `compaction_enabled=True`。
- 提供了 `llm_client`，或使用 fallback summary。

compaction 做两件事：

1. Pre-Compaction Memory Flush
2. Summary Writeback

### 16.1 Pre-Compaction Memory Flush

在压缩前，context manager 会先让 LLM 提取重要信息。

然后调用：

```python
memory_sys.flush_from_context(...)
```

目的：

- 避免压缩时丢掉对主人重要的信息。
- 把阶段性结果写入 daily_log。
- 让 memory system 判断是否写 core / domain_case。

### 16.2 Summary Writeback

之后 context manager 会：

- 对旧消息生成摘要。
- 把摘要作为 `TranscriptEntry(entry_type="compaction", role="system")` 写回 session。

下一次 prepare 时：

- `_entries_to_messages(...)` 会找到最新 compaction entry。
- 在上下文前面加入摘要 system message。
- 只保留 compaction 之后的原始消息。

## 17. compaction boundary

我们实现了“使用最新 compaction boundary”。

含义：

- 如果一个 session 中存在多个 compaction entry，只以最新的为准。
- 最新 compaction 之前的原始消息不再重复进入上下文。
- 但 compaction 摘要会作为前置 system summary 保留。

这样避免：

- 摘要和旧消息重复。
- 多次压缩后上下文膨胀。

## 18. prepare_messages

入口：

```python
prepare_messages(group_id, agent_id, messages, query=None, user_id="default")
```

用途：

- 对内存中的 messages 直接做 context pipeline。
- 不依赖 session transcript。
- 方便测试和未来 agent 层直接调用。

同样会：

- normalize。
- limit turns。
- inject memories。
- assemble budget。

返回结构同样包含 budget metadata。

## 19. get_status

入口：

```python
get_status(group_id, agent_id, session_id)
```

返回：

- 当前 token 数。
- 是否需要 compaction。
- soft threshold。
- max turns。
- total token budget。
- system prompt path。

用于调试和前端状态展示。

## 20. 与 SessionManager 的边界

ContextManager 使用 SessionManager：

- 读取 transcript。
- 写回 compaction entry。

但不改变 SessionManager 的核心语义：

- 不管理 session 生命周期。
- 不决定 session 是否归档。
- 不负责用户会话列表。

## 21. 与 MemorySystem 的边界

ContextManager 使用 MemorySystem：

- `get_core_memories(...)` 必读 core。
- `search(... include_core=False)` 按需拿 daily/cases。
- `flush_from_context(...)` 在 compaction 前写记忆。

但不负责：

- core 的 user_global / user_group 判定。
- daily_log 是否 checkpoint_enabled。
- domain_case 是否满足完成态和结构化规则。
- memory 存储路径。

## 22. 测试情况

测试目录：

```text
backend_test/context_manager/
```

文件：

```text
helpers.py
conftest.py
test_context_policy_and_prompt.py
test_context_history_pipeline.py
test_context_memory_injection.py
test_context_budget_assembly.py
test_context_compaction.py
```

测试框架：

- pytest

测试覆盖：

### 22.1 policy 和 prompt

- policy 缺失时 fallback。
- policy 覆盖生效。
- system prompt 从配置路径加载。

### 22.2 history pipeline

- transcript 规范化。
- leading system 保留。
- 孤立 assistant/tool 处理。
- 按完整 turn 截断。
- 不出现 user/assistant 不配对的截断结果。

### 22.3 memory injection

- core memory block 注入。
- related memory block 注入。
- core 走必读，不重复走 search core。
- memory disabled 时不注入。

### 22.4 budget assembly

- 动态预算会把剩余 token 优先返还给 recent turns。
- token 压力下 core 尽量保留。
- tool results 先被裁剪。
- 返回 budget metadata。

### 22.5 compaction

- 超阈值时触发 compaction。
- compaction 前调用 memory flush。
- 写回 compaction entry。
- 下次 prepare 使用最新 compaction boundary。

常用命令：

```powershell
py -m pytest backend_test\context_manager -q
```

已知某次结果：

```text
19 passed
```

曾见 warning：

- `.pytest_cache` 权限相关 warning。
- 不影响 context manager 业务测试结论。

## 23. 已确认设计决策

1. context manager 是 LLM 调用前的阀门。

2. 历史截断必须按完整 turn，不做简单数组切片。

3. core memory 必读。

4. daily_log 和 domain_case 按需检索。

5. core 不再通过 search 竞争上下文位置。

6. tool results 是最优先裁剪的内容。

7. 预算不是固定切块，而是动态回收和返还。

8. prompt 采用文件注入设计，第一版只管理 system prompt。

9. compaction 是最后一道高成本防线。

10. compaction 前必须尝试 memory flush，避免重要信息丢失。

## 24. 当前已知注意点和 TODO

### 24.1 前端可观测 memory trace

当前 context manager 能注入 memory，但前端不一定能看到 retrieval card。

后续如果要从前端测试新 memory，需要：

- context manager 返回 memory trace。
- agent SSE 发出 retrieval event。
- 前端复用 RetrievalCard 展示 `memory_type`、`scope`、`source_path`。

### 24.2 user_id 默认值

当前部分接口还有 `user_id="default"` 默认参数。

长期应由调用方显式传入真实 user_id。

### 24.3 prompt 扩展

当前只做 system prompt。

后续问答 agent 层可以再扩展：

- task prompt。
- tool prompt。
- domain prompt。
- answer format prompt。

### 24.4 compaction 质量

当前 compaction 可用 fallback summary。

后续可以增强：

- 更严格摘要 prompt。
- 结构化摘要 schema。
- 摘要质量测试。
- 防止摘要丢失关键约束。

### 24.5 编码问题

部分旧文件在 PowerShell 中显示过中文乱码。

后续需要确认：

- 源文件实际保存为 UTF-8。
- prompt、policy、notes 在编辑器中显示正常。
- 测试读取中文 marker 时没有被乱码污染。
