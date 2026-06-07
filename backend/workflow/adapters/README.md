# Workflow Adapters

这里放 workflow 对外边界适配器。

当前职责：

- `workflow_registry_projection.py`
  - `ExecutionPayload -> ContextRegistryEntry[]`
  - 只投影 `question_object` 和 `evidence_ref`
- `workflow_registry_consumer.py`
  - workflow 从 registry 读取哪些对象、怎么解释
  - 只保留 binding 的 `question_object` 复用和 evidence reuse

约束：

- 这里定义 workflow 与 registry 的边界
- 不负责 registry 持久化实现
- 不把 registry 当作 slot layer、summary layer 或 working memory
