# Workflow Adapters

这里放 workflow 对外边界适配器。

当前职责：

- `workflow_registry_projection.py`
  - `ExecutionPayload -> ContextRegistryEntry[]`
- `workflow_registry_consumer.py`
  - workflow 从 registry 读取哪些对象、怎么解释

约束：

- 这里定义 workflow 与 registry 的边界
- 不负责 registry 持久化实现
