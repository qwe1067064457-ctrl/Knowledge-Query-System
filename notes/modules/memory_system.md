# Memory System 模块记录

最后整理：2026-05-12

本文件只记录 `memory_system` 相关信息，不混入 session manager 或 context manager 的实现细节。

## 1. 模块定位

`MemorySystem` 是长期记忆模块，负责把会话和上下文中沉淀出的重要信息写入可复用记忆，并在后续问答中检索或注入。

它和 session 的区别：

- session 保存完整原始对话。
- memory 保存提炼后的长期有效信息、阶段日志、可复用案例。

它和 context manager 的区别：

- memory system 负责存储、检索、策略判断。
- context manager 负责在每次 LLM 调用前决定怎么注入这些记忆。

## 2. 当前代码位置

主目录：

```text
backend/memory_system/
```

文件：

```text
backend/memory_system/__init__.py
backend/memory_system/memory_service.py
backend/memory_system/policy_loader.py
backend/memory_system/policy.default.json
backend/memory_system/RULES.md
```

兼容桥：

```text
backend/context/memory_system.py
```

注意：

- 新的唯一主模块是 `backend/memory_system/`。
- `backend/context/memory_system.py` 只应作为兼容桥，不应继续承载新逻辑。

## 3. 为什么从 context 拆出来

我们曾确认：memory 模块工作量明显增加，不适合继续放在 `backend/context/`。

拆分后的边界：

- `context`：会话上下文编排、截断、预算、compaction。
- `memory_system`：记忆存储、检索、checkpoint 写入、policy 加载。
- `session`：原始会话和 transcript 持久化。

这让后续扩展组管理、记忆策略、记忆检索、case 索引时更清晰。

## 4. 三类记忆

当前只保留三类记忆：

```text
core
daily_log
domain_case
```

不再使用旧的：

```text
memory/MEMORY.md
memory/cases.md
按 agent 镜像的 MEMORY.md
按 agent 镜像的 cases.md
```

旧文件可以作为历史资料存在，但不再作为新 memory system 的主语义来源。

## 5. 记忆作用域

### 5.1 user_global

含义：

- 属于某个用户。
- 跨 group 可见。
- 适合稳定偏好、长期习惯、持续身份信息。

例子：

- 用户偏好简洁回答。
- 用户希望默认输出中文。
- 用户长期关注某类表达风格。

路径：

```text
storage/users/{user_id}/global/core.json
```

### 5.2 user_group

含义：

- 属于某个用户。
- 只在指定 group 内可见。
- 适合某个知识库或领域内的个人规则、阶段状态、当前项目偏好。

例子：

- 用户在 law 组里希望优先引用合同条款。
- 用户在 medical 组里希望输出风险分层。

路径：

```text
storage/users/{user_id}/groups/{group_id}/core.json
storage/users/{user_id}/groups/{group_id}/daily_logs/YYYY-MM-DD.jsonl
```

### 5.3 group_shared

含义：

- 属于某个 group。
- 组内共享。
- 不属于某个单独用户。

适合：

- 案例记忆。
- 判例。
- 病例。
- 已沉淀的领域案例。

当前代码路径：

```text
storage/groups/{group_id}/shared/domain_cases.jsonl
```

## 6. 当前存储结构

当前代码以 `storage` 为根：

```text
storage/
  users/
    {user_id}/
      global/
        core.json
      groups/
        {group_id}/
          core.json
          daily_logs/
            YYYY-MM-DD.jsonl

  groups/
    {group_id}/
      meta.json
      shared/
        domain_cases.jsonl
```

说明：

- `core.json` 是 JSON 数组。
- `daily_logs/*.jsonl` 是 JSONL。
- `domain_cases.jsonl` 当前仍是单个 JSONL 文件。

重要说明：

- 我们之前讨论过更优方案：`domain_case` 改成“单 case 单文件 + 一个轻量索引文件”。
- 当前代码检查结果显示，现实现仍是 `domain_cases.jsonl`。
- 因此本 note 按当前代码写，同时把“单 case 单文件 + index + 后续 SQLite”列入 TODO。

## 7. 不再使用 default 用户兜底

我们明确过：

- 不保留 default 用户作为共享兜底。
- 没有“所有用户都能读 default 记忆”的长期语义。

当前代码里某些方法仍有 `user_id="default"` 默认参数，这是为了兼容调用方没有传 user_id 的旧链路。

正确的新链路应显式传入真实 `user_id`。

## 8. 不再按 agent 分类记忆

我们确认过：

- 不同知识库直接用 `group_id` 隔离。
- 不把 `agent_id` 当成 memory 分类维度。
- `agent_id` 可以保留在 session 或运行链路中，方便不同 prompt、不同 agent 流程扩展。

因此 memory system 中：

- `write_daily_log(...)` 接收 `agent_id` 只是兼容旧接口，内部不参与路径分类。
- `search(...)` 接收 `agent_id` 也是兼容旧接口，内部不参与 memory 检索范围。

## 9. Policy 驱动

为了避免把法律、医学等关键词写死在代码里，我们引入了组元数据 policy。

规则来源两层：

1. 默认规则：

```text
backend/memory_system/policy.default.json
```

2. group 覆盖规则：

```text
storage/groups/{group_id}/meta.json
```

`meta.json` 中使用：

```json
{
  "memory_policy": {
    "enabled_memory_types": ["core", "daily_log", "domain_case"],
    "core": {
      "explicit_markers": ["以后", "默认"],
      "group_scope_keywords": ["法律", "法条"],
      "min_candidate_length": 6,
      "max_candidate_length": 120
    },
    "daily_log": {
      "checkpoint_enabled": true
    },
    "domain_case": {
      "completion_markers": ["已完成", "结论"],
      "structural_markers": ["问题", "分析", "结论"],
      "case_markers": ["案例", "判例", "病例"]
    }
  }
}
```

### 9.1 enabled_memory_types

控制哪些 memory type 启用。

例如：

```json
["core", "daily_log"]
```

表示禁用 `domain_case` 的自动写入和检索。

### 9.2 core.explicit_markers

显式长期信号词。

含义：

- 只有用户消息中出现这些 marker，才可能被提取为 core memory。
- 这样避免系统把普通闲聊误写成长期记忆。

例子：

```text
以后
默认
始终
统一
偏好
习惯
```

### 9.3 core.group_scope_keywords

用于判断 core memory 是 `user_global` 还是 `user_group`。

命中 group scope keyword：

- 写入 `user_group`

未命中：

- 写入 `user_global`

示例：

- “以后法律问题默认先列风险点”命中法律相关关键词，倾向 `user_group`。
- “以后回答默认用中文”没有明显领域限定，倾向 `user_global`。

### 9.4 min_candidate_length / max_candidate_length

用于过滤 core 候选文本长度。

目的：

- 太短的文本信息量不足，容易误写。
- 太长的文本通常不是稳定偏好，而是整段任务内容。

当前默认：

```text
min_candidate_length = 6
max_candidate_length = 120
```

它们只是第一版粗过滤，不是语义质量判断。

### 9.5 daily_log.checkpoint_enabled

当前 daily_log 第一版只有这个配置项。

含义：

- `true`：context flush / checkpoint 时可以写 daily log。
- `false`：flush 仍可执行，但不写 daily log。

### 9.6 domain_case 规则

`domain_case` 自动写入需要同时满足“完成态”和“结构化/案例信号”。

相关字段：

- `completion_markers`：表示任务已有阶段性结论或完成。
- `structural_markers`：表示内容具备结构，例如问题、分析、结论。
- `case_markers`：表示内容像案例、判例、病例等可复用对象。

这样做是为了避免把普通回答都沉淀成 case。

## 10. PolicyLoader

实现位置：

```text
backend/memory_system/policy_loader.py
```

核心行为：

- 读取 `policy.default.json`。
- 读取 `storage/groups/{group_id}/meta.json`。
- 取其中的 `memory_policy`。
- 对默认规则和 group 覆盖规则做 deep merge。
- group meta 缺失时完全 fallback 到默认规则。
- group meta 损坏或非法 JSON 时回退默认规则，不抛异常。

测试覆盖：

- meta 缺失 fallback。
- 局部覆盖 deep merge。
- invalid JSON fallback。
- `enabled_memory_types`、`core.*`、`daily_log.*`、`domain_case.*` 可读取。

## 11. 已实现公开接口

### write_core_memory

```python
write_core_memory(
    *,
    user_id,
    group_id,
    scope,
    content,
    title=None,
    tags=None,
    source_session_id=None,
    metadata=None,
) -> None
```

行为：

- `scope` 只能是 `user_global` 或 `user_group`。
- `user_global` 写入：

```text
storage/users/{user_id}/global/core.json
```

- `user_group` 写入：

```text
storage/users/{user_id}/groups/{group_id}/core.json
```

去重逻辑：

- 基于规范化后的 content 去重。
- 如果已有同内容记录，会更新 title、tags、metadata、source 等信息。

### write_daily_log

```python
write_daily_log(
    group_id,
    agent_id,
    content,
    target_date=None,
    *,
    user_id="default",
    title=None,
    tags=None,
    source_session_id=None,
    metadata=None,
) -> None
```

行为：

- 写入当前用户 + 当前 group 的 daily log。
- `agent_id` 不参与路径分类。
- `target_date` 不传时使用当天。

路径：

```text
storage/users/{user_id}/groups/{group_id}/daily_logs/YYYY-MM-DD.jsonl
```

### write_to_daily_log

```python
write_to_daily_log(...)
```

兼容接口。

当前语义：

- 代理到 `write_daily_log(...)`。
- 与 `write_daily_log(...)` 落同一路径。

这个接口是之前 context flush 调用时暴露出缺失后补上的。

### write_domain_case

```python
write_domain_case(
    *,
    group_id,
    title,
    content,
    tags=None,
    source_session_id=None,
    metadata=None,
) -> None
```

当前代码行为：

- 写入 group shared domain case。
- 当前文件是：

```text
storage/groups/{group_id}/shared/domain_cases.jsonl
```

已讨论但需要继续核对实现的演进方向：

- 单 case 单文件。
- 轻量索引文件。
- 后续 SQLite 迁移 TODO。

### get_core_memories

```python
get_core_memories(*, user_id, group_id) -> list[MemoryEntry]
```

返回：

- 当前用户的 `user_global` core。
- 当前用户当前 group 的 `user_group` core。

不返回：

- 其他用户的 core。
- 其他 group 的 user_group core。
- default 用户兜底 core。

我们讨论过：

- core 是必读层。
- 不应依赖 search 打分后才可能进入上下文。
- `user_global + user_group` 同时存在时，在当前 group 下两者都注入。
- 切换到其他 group 时，只保留 `user_global`，不带入原 group 的 `user_group`。

### search

```python
search(
    group_id,
    agent_id,
    query,
    top_k=5,
    min_score=0.1,
    date_range=None,
    time_decay_half_life=30,
    use_mmr=True,
    mmr_lambda=0.7,
    *,
    user_id="default",
    include_core=True,
    include_daily_logs=True,
    include_domain_cases=True,
) -> list[MemoryEntry]
```

职责：

- 这是新 memory system 的检索核心。
- 它不是单独的 `memory_retrieve.py` 模块，而是在 `MemorySystem.search(...)` 内实现。

内部检索：

```text
search(...)
  -> _search_core_memories(...)
  -> _search_daily_logs(...)
  -> _search_domain_cases(...)
  -> _mmr_deduplicate(...)
```

### _search_core_memories

作用：

- 检索 core memory。
- 当前会参与打分。
- 有额外 boost，保证 core 在搜索场景中更容易靠前。

注意：

- context manager 正常注入时，core 走 `get_core_memories(...)` 必读。
- 因此 context manager 调用 search 时会使用 `include_core=False`。
- search core 主要给调试、独立检索、未来 UI 搜索使用。

### _search_daily_logs

作用：

- 检索当前 user + group 下的 daily logs。
- 支持 `date_range`。
- 使用简单 BM25 风格评分。
- 支持时间衰减，越新的日志权重越高。

### _search_domain_cases

作用：

- 检索当前 group shared 的 domain cases。
- 当前从 `domain_cases.jsonl` 中逐行读取。
- 跨 group 不可见。

### _mmr_deduplicate

作用：

- 对搜索结果做去重和多样性控制。
- 避免 top_k 里全是高度相似的内容。

## 12. get_recent_memories

```python
get_recent_memories(group_id, agent_id, days=7, *, user_id="default")
```

作用：

- 读取最近 N 天 daily log。
- 当前仍保留 `agent_id` 参数兼容旧接口，但不参与路径分类。

## 13. capture_checkpoint

```python
capture_checkpoint(
    *,
    group_id,
    agent_id,
    user_id,
    messages,
    summary,
    source_session_id=None,
) -> dict
```

这是 memory 写入触发的核心入口。

它会读取 group policy，然后决定：

1. 是否写 daily_log。
2. 是否从 user messages 提取 core。
3. 是否从 summary / assistant result 提取 domain_case。

### daily_log 写入时机

当前策略：

- context flush / checkpoint 时写。
- `summary` 不是空，也不是 `NO_REPLY`。
- `enabled_memory_types` 包含 `daily_log`。
- `daily_log.checkpoint_enabled == true`。

daily_log 的定位：

- 记录时间事件。
- 记录阶段性过程。
- 是后续 core / domain_case 的候选来源之一，但当前实现也可以直接从 flush messages 中抽取。

### core 写入时机

当前策略：

- 从 user messages 中提取。
- 必须命中 `core.explicit_markers`。
- 必须满足长度范围。
- 再根据 `core.group_scope_keywords` 判断写入 `user_global` 还是 `user_group`。

我们讨论过的原则：

- core 只存稳定偏好、长期规则、持续身份信息。
- core 不应把普通任务内容都写进去。
- 第一版不做复杂 LLM 判断，用显式 marker 保守触发。

### domain_case 写入时机

当前策略：

- 从 summary 和 assistant 内容中判断。
- 需要命中完成态 marker。
- 还要具备结构化 marker 或 case marker。

适合写入 domain_case 的情况：

- 一个法律问题已经形成结论。
- 一个判例或案例已经结构化沉淀。
- 一个医学病例有问题、分析、结论。

不适合写入：

- 普通闲聊。
- 未完成任务。
- 单轮无结构回答。

## 14. flush_from_context

```python
flush_from_context(
    group_id,
    agent_id,
    context_summary,
    *,
    user_id="default",
    source_session_id=None,
    messages=None,
) -> dict
```

作用：

- 给 context manager 调用。
- 将 compaction 前或 flush 时提取出的摘要写入 memory system。
- 内部调用 `capture_checkpoint(...)`。

返回信息包含：

- 是否 flushed。
- 写入 daily_log 情况。
- core 写入数量。
- domain_case 是否写入。

## 15. get_storage_fingerprint

```python
get_storage_fingerprint(*, group_id, user_id) -> str
```

作用：

- 计算当前用户 + 当前 group 相关 memory 文件的摘要。
- 可用于缓存失效、调试或后续前端刷新判断。

当前纳入：

- user_global core。
- user_group core。
- daily log。
- domain_cases.jsonl。

## 16. 与 context manager 的注入关系

当前注入策略：

- `core`：通过 `get_core_memories(...)` 必读注入。
- `daily_log`：通过 `search(... include_core=False)` 按需检索。
- `domain_case`：通过 `search(... include_core=False)` 按需检索。

我们讨论过是否需要 extended core：

```text
core -> extended core -> daily -> cases
```

当前结论：

- 暂时不加 extended core。
- 避免层级过多。
- 当前用 core 必读 + daily/cases 按需即可。
- 如果未来 core 变大，再考虑把 core 拆成 `core pinned` 和 `core searchable`。

## 17. 与前端检索卡片的关系

旧链路：

- `graph.memory_indexer`
- `memory/MEMORY.md`
- RAG retrieval card

新链路：

- `MemorySystem.search(...)`
- `ContextManager._inject_memories(...)`
- 注入到 system context

当前状态：

- 新 memory system 已有底层搜索和上下文注入。
- 前端可观测 retrieval trace / SSE memory card 需要额外薄层支持。
- 旧 retrieval card 的展示协议可以复用，但 memory 数据源应改成新 memory system。

## 18. 测试情况

测试目录：

```text
backend_test/memory_system/
```

文件：

```text
helpers.py
test_memory_storage_paths.py
test_memory_scope_and_visibility.py
test_memory_search_switches.py
test_memory_context_integration.py
test_memory_policy_loader.py
```

测试框架：

- unittest

注意：

- 用户后来偏好 pytest，但 memory_system 这批测试是在已有 unittest 体系上扩展的。
- 后续如重构，可迁移到 pytest。

测试覆盖：

- core / daily_log / domain_case 主路径写入。
- `write_to_daily_log()` 与 `write_daily_log()` 落同一路径。
- user_global 跨组可见。
- user_group 只在当前 group 可见。
- daily_log 按 user + group 隔离。
- domain_case 组内共享、跨组不可见。
- include_core / include_daily_logs / include_domain_cases 开关。
- enabled_memory_types 禁用某类后不写入或不检索。
- policy.default fallback。
- group meta deep merge。
- invalid meta fallback。
- checkpoint_enabled 开关。
- core marker 提取。
- domain_case 完成态 + 结构化联合判定。

常用命令：

```powershell
py -m unittest discover -s backend_test\memory_system -p "test_*.py"
```

已知某次结果：

```text
Ran 30 tests
OK (skipped=2)
```

跳过项主要是：

- core 自动晋升策略尚未完全定稿。
- domain_case 自动晋升策略尚未完全定稿。

## 19. 已确认设计决策

1. memory 不按 agent 分类。

2. `group_id` 是领域和知识库隔离主维度。

3. `user_global` 是用户跨组记忆。

4. `user_group` 是用户在某个 group 内的记忆。

5. `group_shared` 是组内共享资源，主要承载 domain_case。

6. core 是必读层，不靠 search 竞争进入上下文。

7. daily_log 和 domain_case 是按需检索层。

8. 不保留 default 用户兜底语义。

9. 不再测试旧 `MEMORY.md / cases.md` 镜像文件。

10. 写入时机要 policy 驱动，不在代码里硬编码 law、medical 等词。

## 20. 当前已知注意点和 TODO

### 20.1 domain_case 存储演进

当前代码：

```text
storage/groups/{group_id}/shared/domain_cases.jsonl
```

已讨论过的更好方向：

```text
storage/groups/{group_id}/shared/domain_cases/
  index.json
  cases/
    {case_id}.json
```

后续 TODO：

- 单 case 单文件。
- 轻量 index。
- 再后续可迁移 SQLite。
- 更新 `write_domain_case`、`_search_domain_cases`、`get_storage_fingerprint`。
- 同步更新 memory tests 和 notes。

### 20.2 policy.default.json 编码

PowerShell 输出曾出现中文乱码。

后续应确认：

- 文件实际编码为 UTF-8。
- 中文 marker 在 Python 读取后是否正常。
- 如果默认 policy 已被乱码污染，需要重新写 UTF-8。

### 20.3 前端可观测性

当前新 memory system 是后端注入能力。

如果要从前端测试 memory，需要补：

- memory seed/debug API，或通过正式会话触发 flush。
- retrieval trace。
- SSE retrieval event。
- 前端 card 显示 source、scope、memory_type。

### 20.4 自动写入策略

第一版保守策略已经有：

- core：显式 marker。
- daily_log：checkpoint flush。
- domain_case：完成态 + 结构化/案例 marker。

但更智能的策略仍待讨论：

- 多轮重复偏好晋升 core。
- LLM 判断重要性。
- 用户确认后写入。
- domain_case 的质量评分和去重。
