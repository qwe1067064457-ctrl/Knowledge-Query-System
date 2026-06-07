# Session Working Memory

这个目录承接 `QA Runner V2` 的短程语义记忆层。

职责：

- 存储短程高价值语义单元
- 提供 append / supersede / stale / forget
- 为 `ContextBindingPower` 提供 relevant set 候选

文件职责：

- `models.py`
  - `WorkingMemoryEntry`
  - `WorkingMemoryHead`
  - `SessionWorkingMemory`
- `store.py`
  - `working_memory.jsonl + head.json` 读写
- `writer.py`
  - 从当前 turn 投影 entry
- `resolver.py`
  - relevant set 规则筛选
- `retention.py`
  - retention / supersede / budget 控制
