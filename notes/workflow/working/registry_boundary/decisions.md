# Registry Boundary Decisions

## D1. Registry metadata keeps stable flat keys and adds explicit namespaces

- Decision:
  - registry entry metadata 继续保留平铺字段，避免破坏现有 stable dict contract。
  - 同时新增：
    - `workflow_summary`
    - `registry_convenience`
- Why:
  - 仅靠平铺字段时，workflow owner 输出和 entry 级便利字段混在一起，边界不清。
  - 直接移除平铺字段又会扩大兼容风险。
- Impact:
  - 后续消费者可以优先依赖显式分层。
  - 老消费者仍可继续读平铺字段。

## D2. Current registry formal boundary stops at entry writing semantics

- Decision:
  - 本 goal 只把正式边界收清到 `workflow -> registry entry` 的写入口径。
  - 不继续扩大到 session / memory / context 更大集成层。
- Why:
  - 当前高频入口在 `graph.agent` 的 entry 构建。
  - `workflow.runners` 对 registry 的读取已经主要依赖通用 entry 字段，不需要为本 goal 大改 context 主结构。
- Impact:
  - 本 goal 可以在不重做 `ContextManager` / `ContextRegistryManager` 的前提下完成。
  - 后续如果需要更深集成，应作为新 goal 单独处理。
