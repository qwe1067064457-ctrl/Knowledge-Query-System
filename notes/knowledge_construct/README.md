# Knowledge Construct 记录

最后整理：2026-05-12

本目录记录“知识库采集与落盘”相关经验，和业务模块实现文档分开维护。

当前拆分为两个子主题：

- `notes/knowledge_construct/crawler/`
  - 记录爬虫实现、来源筛选、试错过程、反爬反馈、增量抓取问题
- `notes/knowledge_construct/knowledge/`
  - 记录知识库目录结构、原文保留原则、索引规范、分组与分类约定

建议阅读顺序：

1. 先读 `crawler/README.md`
   - 了解哪些来源真实可用，哪些来源只是检索入口，哪些来源会被反爬拦截
2. 再读 `knowledge/README.md`
   - 了解抓下来的内容应该如何落盘、分类、保留原文与维护索引

这两部分的边界：

- `crawler` 关注“怎么抓到”
- `knowledge` 关注“抓到以后怎么组织、怎么保留、怎么让后续 agent 能用”
