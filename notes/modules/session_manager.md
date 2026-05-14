# Session Manager 模块记录

最后整理：2026-05-12

本文件只记录 `SessionManager` 相关信息，不混入 memory system 或 context manager 的实现细节。

## 1. 模块定位

`SessionManager` 是会话管理模块，负责保存和读取用户与系统之间的原始对话记录。

它的职责是“事实记录”，不是“长期记忆”：

- 保存完整 transcript，包括 user、assistant、tool、system、compaction 等条目。
- 维护会话元数据，例如所属用户、所属组、所属 agent、状态、轮次数、token 总数。
- 提供会话恢复能力，让系统重启后仍能从磁盘恢复会话和消息。
- 提供基础隔离，确保不同 `group_id`、`agent_id`、`user_id` 的会话不会串读。

我们明确过：会话不是记忆层。会话可以作为 memory system 的输入来源，但它本身只是原始活动日志。

## 2. 当前代码位置

主实现：

- `backend/context/session_manager.py`

相关数据结构：

- `backend/context/dataclasses.py`
  - `Session`
  - `SessionStatus`
  - `TranscriptEntry`
  - `ToolCall`

测试目录：

- `backend_test/session_test/`

## 3. 目录和存储结构

`SessionManager` 初始化时接收 `base_storage_path`。实际数据按 group 和 agent 分层：

```text
storage/
  groups/
    {group_id}/
      agents/
        {agent_id}/
          sessions/
            index.db
            {session_id}.jsonl
            {session_id}.meta.json
```

其中：

- `{session_id}.jsonl`：逐行保存 transcript entry。
- `{session_id}.meta.json`：保存 session 的元信息和 metadata。
- `index.db`：SQLite 索引，按 group + agent 独立维护。

这种设计的含义：

- `group_id` 是知识库或领域隔离维度。
- `agent_id` 是运行时 agent 维度，保留给后续不同 agent、不同 prompt、不同流程扩展。
- `user_id` 是会话所有者，用于用户会话列表和权限关联。
- session 存储没有放到 memory system 下，因为 session 与 memory 是两个模块。

## 4. SQLite 索引

每个 `group_id + agent_id` 对应一个独立的 `index.db`。

当前 `sessions` 表包含：

```text
id
group_id
user_id
agent_id
created_at
last_active_at
archived_at
status
turn_count
total_tokens
```

当前索引：

```text
idx_sessions_user_status_activity(user_id, status, last_active_at DESC)
```

用途：

- 快速列出某个用户的会话。
- 支持按状态筛选 active / archived。
- 按最近活跃时间倒序返回。

## 5. 会话 ID

创建会话时生成类似：

```text
session_YYYYMMDD_HHMMSS_<8位随机hex>
```

例如：

```text
session_20260508_150850_b7ab9258
```

这个 ID 兼顾可读性和唯一性。

## 6. 已实现公开接口

### create_session

```python
create_session(group_id, agent_id, user_id, metadata=None) -> Session
```

行为：

- 校验 `group_id` 和 `agent_id` 的路径安全性。
- 创建 session id。
- 创建空 transcript JSONL 文件。
- 创建 `.meta.json` 元数据文件。
- 写入 SQLite session 行。
- 初始状态为 `SessionStatus.ACTIVE`。
- 初始 `turn_count = 0`，`total_tokens = 0`。

### get_session

```python
get_session(session_id, group_id, agent_id) -> Optional[Session]
```

行为：

- 只在指定 `group_id + agent_id` 的 SQLite 中查找。
- 找不到返回 `None`。
- 找到后读取 `.meta.json`，把 metadata 合并回 `Session`。

重要语义：

- 错误 group 或错误 agent 读取不到 session。
- 这是权限隔离和领域隔离的基础。

### append_entry

```python
append_entry(group_id, agent_id, entry) -> None
```

行为：

- 校验 `entry.group_id == group_id`。
- 将 `TranscriptEntry` 追加到 `{session_id}.jsonl`。
- 更新 SQLite：
  - `last_active_at`
  - `total_tokens`
  - 如果 `entry.role == "user"`，则 `turn_count + 1`

关键决策：

- `turn_count` 只统计 user 消息。
- assistant、tool、system 不增加轮次。
- `token_count=None` 时不增加 `total_tokens`，也不应报错。

兼容行为：

- 如果 append 时 SQLite 中没有 session 行，当前实现会以 legacy 方式补建 session 行。
- 这种情况下 `user_id` 会使用 `"default"`。
- 这属于兼容旧数据的逻辑，不是推荐的新写入路径。

### get_transcript

```python
get_transcript(
    group_id,
    agent_id,
    session_id,
    limit=None,
    from_id=None,
    include_compacted=True,
    since_timestamp=None,
) -> list[TranscriptEntry]
```

行为：

- 从指定 group + agent 下读取 `{session_id}.jsonl`。
- 文件不存在时返回空列表。
- 支持：
  - `limit`
  - `from_id`
  - `include_compacted`
  - `since_timestamp`

语义：

- transcript 是 append-only 风格的客观记录。
- compaction entry 也属于 transcript，只是 context manager 可选择过滤或作为边界处理。

### list_user_sessions

```python
list_user_sessions(group_id, agent_id, user_id, status=None, limit=20) -> list[Session]
```

行为：

- 只列出指定 group + agent + user 下的会话。
- 支持按 `SessionStatus` 筛选。
- 默认按 `last_active_at DESC` 排序。

用途：

- 用户会话列表。
- 会话恢复入口。
- 验证多用户、多组、多 agent 的隔离。

### archive_session

```python
archive_session(session_id, group_id, agent_id) -> None
```

行为：

- 将状态改为 `ARCHIVED`。
- 设置 `archived_at`。

已经讨论并确认的产品语义：

- 归档不是删除。
- 归档不是只读锁。
- 归档表示低活跃、收纳、列表筛选意义上的状态。
- 用户仍然可以向归档会话追加消息。

这个点曾经触发过测试失败：测试最早假设“归档后禁止写入”，但后来我们确认这不符合你的产品定义，因此测试应改为“归档后仍可写入”。

### delete_session

```python
delete_session(session_id, group_id, agent_id) -> None
```

行为：

- 删除 transcript JSONL。
- 删除 `.meta.json`。
- 删除 SQLite 中的 session 行。

删除后：

- `get_session(...)` 返回 `None`。
- `get_transcript(...)` 返回空列表。

## 7. 路径安全

`group_id` 和 `agent_id` 会经过路径段校验。

当前允许：

```text
A-Z
a-z
0-9
_
.
-
```

非法示例：

```text
../bad
bad/path
```

非法路径段应抛 `ValueError`。

这条规则用于防止路径穿越，避免把 session 文件写到预期目录之外。

## 8. 六项核心职责

我们围绕 session manager 确认过六项职责。

### 8.1 多领域隔离

含义：

- `law` 会话和 `medical` 会话不能串数据。
- 即使是同一用户，跨 group 也不能读到对方 transcript。

已测试行为：

- 同一用户分别创建 law 和 medical session。
- 只向 law 写消息。
- medical transcript 长度仍为 0。
- 使用错误 group 读取 law session 返回空或 None。

### 8.2 会话生命周期

含义：

- 创建。
- 查询。
- 归档。
- 删除。

已确认产品语义：

- create 后状态是 active。
- archive 后状态是 archived，`archived_at` 非空。
- archive 后仍可 append。
- delete 后 session 和 transcript 都不可恢复。

### 8.3 消息持久化

含义：

- append 的消息必须落盘。
- 重新读取 transcript 时字段保持一致。
- 多条消息顺序不变。

关键字段：

- `session_id`
- `group_id`
- `role`
- `entry_type`
- `content`
- `token_count`
- `timestamp`
- `metadata`

### 8.4 会话恢复

含义：

- 不是靠内存常驻。
- 重启或重新实例化 `SessionManager` 后，应从磁盘和 SQLite 恢复。

已测试行为：

- 创建 session 并 append 后，重新 new 一个 `SessionManager` 指向同一临时 storage。
- `get_session(...)` 能取回 session。
- `get_transcript(...)` 能取回消息。
- `list_user_sessions(...)` 能列出该用户会话。

### 8.5 轮次管理

含义：

- 轮次按 user 消息统计。
- assistant/tool/system 不算轮次。

已修正过的理解：

- 如果连续追加两条 user 消息，中间有 assistant/tool/system，最终 `turn_count` 应为 2。
- 如果只有 assistant/tool/system，`turn_count` 不增长。

### 8.6 权限关联

当前还没有独立鉴权系统，因此这里的“权限”先按可观测边界定义：

- 只能通过正确的 `group_id + agent_id` 路径访问会话。
- `user_id` 决定 `list_user_sessions(...)` 的可见性。
- 非法路径段直接拒绝。

## 9. 和 memory system 的边界

SessionManager 不负责：

- 判断什么内容值得成为长期记忆。
- 写入 core memory。
- 写入 daily log。
- 写入 domain case。
- 做语义检索。

它只提供原始 transcript。memory system 可以从 transcript 或 context flush 中抽取记忆。

## 10. 和 context manager 的边界

ContextManager 会调用 SessionManager：

- 读取 transcript。
- 识别 compaction boundary。
- 在需要时写回 compaction entry。

但 SessionManager 不知道上下文预算，也不负责裁剪。

## 11. 测试情况

测试目录：

```text
backend_test/session_test/
```

文件：

```text
conftest.py
pytest.ini
test_session_isolation_and_permissions.py
test_session_lifecycle_and_recovery.py
test_session_persistence_and_turns.py
```

测试框架：

- pytest

测试原则：

- 黑盒测试。
- 使用临时目录。
- 不污染真实 `backend/storage/`。
- 每项核心职责至少 1 个正例 + 1 个反例。
- 未实现接口或不确定需求使用 `xfail` 或 `skip`，不顺手改业务。

常用命令：

```powershell
py -m pytest backend_test\session_test -q
py -m pytest backend_test\session_test --cov=backend/context/session_manager.py --cov-report=term-missing
```

曾经的重要测试调整：

- “归档后禁止写入”不再是正确预期。
- 现在应测试“归档后仍可写入，状态保持 archived”。

## 12. 当前已知注意点

1. `append_entry(...)` 对不存在 session 的兼容补建逻辑会使用 `user_id="default"`。
   - 这是历史兼容，不应作为新链路依赖。

2. `SessionStatus.DELETED` 在枚举中存在，但当前 delete 是物理删除 session 文件和索引行。
   - 未来如果要做回收站，可以再把 delete 改成软删除。

3. `agent_id` 当前仍参与 session 路径隔离。
   - 这和 memory system 不再按 agent 分类并不矛盾。
   - session 是运行链路记录，agent 仍有意义。

4. 中文注释或文件显示可能出现终端编码问题。
   - 以 UTF-8 文件内容为准。
   - 如果 PowerShell 输出乱码，优先用编辑器或明确 UTF-8 读取。

## 13. 后续 TODO

- 明确是否保留 legacy 补建 session 的 `"default"` 行为。
- 如果用户系统上线，应把 `user_id` 从前端或鉴权层稳定传入。
- 如果会话量变大，可考虑全局 session 索引或分页游标。
- 如果需要回收站，再设计 soft delete，而不是当前物理删除。
