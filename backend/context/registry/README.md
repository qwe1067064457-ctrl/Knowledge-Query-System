# Context Registry

这里放 registry entry 的存取与裁剪。

当前定位：

- 跨轮对象锚点层
- 只保留高可靠、可复用的 `question_object` 和 `evidence_ref`

职责：

- `ContextRegistryEntry` / `ContextRegistry` 存储
- registry append / load / prune

不负责：

- workflow 如何投影 entry
- 哪些 entry type 给哪些 power 消费
- claim / planning / review 中间态持久化
- summary / working memory 替代

这些规则由 `workflow/adapters/` 定义。
