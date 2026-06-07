# Registry Boundary Known Issues

- 当前 registry metadata 仍同时存在：
  - 平铺兼容字段
  - `workflow_summary`
  - `registry_convenience`
  这是有意保留的兼容层，不是这轮要清零的重复结构。

- `workflow_summary` 适合承载：
  - `knowledge_scope_status`
  - `binding_summary`
  - `plan_summary`
  - `review_summary`
  - `evidence_summary`

- `registry_convenience` 适合承载：
  - `route`
  - `handling_mode`
  - `channel`
  - `source_type`
  - `query_unit_ids`
  - 以及 entry 对象本身的持久化便利字段

- 如果后续需求已经主要变成：
  - session/memory/context 的更大集成
  - registry 存储结构重做
  那就超出本 goal。
