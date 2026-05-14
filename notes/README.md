# Notes README

`notes/` 是当前项目的主知识库。

现阶段先不追求复杂文档分层，而是坚持一个更轻的原则：

- 深度理解、过程记录、阶段性方案先沉淀在 `notes/`
- `CONTEXT.md` 负责告诉 AI 先读哪些 `notes/`
- `README.md` 负责给人类做总导航
- `docs/` 只接收相对稳定、相对正式的内容

## 当前目录

- [modules](C:/Users/HUAWEI/.codex/worktrees/2a18/Skill-First-Hybrid-RAG/notes/modules/README.md)
  - 普通模块型笔记，如 `context / memory / session / group`
- [intent](C:/Users/HUAWEI/.codex/worktrees/2a18/Skill-First-Hybrid-RAG/notes/intent/README.md)
  - intent 专题：规则、评估、监督、SFT 准备
- [knowledge_construct](C:/Users/HUAWEI/.codex/worktrees/2a18/Skill-First-Hybrid-RAG/notes/knowledge_construct/README.md)
  - 知识库构建专题：爬取、落盘、目录组织
- [working](C:/Users/HUAWEI/.codex/worktrees/2a18/Skill-First-Hybrid-RAG/notes/working/README.md)
  - 中间态、临时方案、尚未稳定的文档
- [archives](C:/Users/HUAWEI/.codex/worktrees/2a18/Skill-First-Hybrid-RAG/notes/archives/README.md)
  - 过期但保留的历史材料

## 推荐阅读顺序

如果是第一次接手这个仓库，建议：

1. 先看 [CONTEXT.md](C:/Users/HUAWEI/.codex/worktrees/2a18/Skill-First-Hybrid-RAG/CONTEXT.md)
2. 再看本页，确认 `notes/` 的目录职责
3. 根据主题进入对应专题：
   - intent：看 [notes/intent/README.md](C:/Users/HUAWEI/.codex/worktrees/2a18/Skill-First-Hybrid-RAG/notes/intent/README.md)
   - knowledge construct：看 [notes/knowledge_construct/README.md](C:/Users/HUAWEI/.codex/worktrees/2a18/Skill-First-Hybrid-RAG/notes/knowledge_construct/README.md)
   - context / memory / session：看 [notes/modules/README.md](C:/Users/HUAWEI/.codex/worktrees/2a18/Skill-First-Hybrid-RAG/notes/modules/README.md)

## 放置规则

- 深度理解、阶段性结论、过程记录：先放 `notes/`
- 临时方案、草稿、尚未沉淀内容：放 `notes/working/`
- 已形成稳定共识的较正式文档：再考虑提炼到 `docs/`
- 明显过期但值得保留的旧文档：移到 `notes/archives/`

## 一句话总结

当前这套文档结构不是“大而全架构”，而是一个以 `notes/` 为中心、由 `CONTEXT.md` 负责导航的轻量知识系统。
