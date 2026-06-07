# knowledge_retrieval 迁移说明

## 当前状态

- `knowledge_retrieval` 不再承担正式检索 owner 责任。
- `HybridRetriever`、`KnowledgeIndexer` 等入口保留为兼容 facade。
- 正式实现位于 `backend/retrieval_infra/`。

## 迁移方向

- parser / chunker / lexical / vector / rerank / queue 全部迁入 `retrieval_infra`
- `knowledge_retrieval` 最终只保留极薄导出层，或在后续版本删除

## 不再允许

- 在本目录继续扩展新的检索 owner 逻辑
- 从旧 `backend/knowledge/...` 直接扫描线上知识源
