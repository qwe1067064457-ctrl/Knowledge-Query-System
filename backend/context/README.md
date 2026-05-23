# Context

`context/` 只负责上下文子系统，不负责 workflow contract，也不负责主回答 prompt 文本。

当前分层：

- `assembly/`
  - 上下文窗口装配、budget、prepare 入口
- `session/`
  - session 生命周期、transcript 与兼容适配
- `registry/`
  - registry entry 存储、读取、裁剪
- `models.py`
  - context 子系统共享模型

约束：

- `context/` 不拥有 workflow schema
- `context/` 不拥有 graph orchestration
- `context/` 不拥有 llm provider 选择
