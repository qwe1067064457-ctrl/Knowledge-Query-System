# Context Registry

这里放 registry entry 的存取与裁剪。

职责：

- `ContextRegistryEntry` / `ContextRegistry` 存储
- registry append / load / prune

不负责：

- workflow 如何投影 entry
- 哪些 entry type 给哪些 power 消费

这些规则由 `workflow/adapters/` 定义。
