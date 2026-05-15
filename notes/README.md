# Notes README

`notes/` 是当前项目最核心的知识库。

现阶段不追求复杂文档分层，而是坚持一个更轻的原则：

- 深度理解、过程记录、阶段结论先沉淀在 `notes/`
- `CONTEXT.md` 负责告诉 AI 从哪里进入 `notes/`
- `README.md` 负责给人类做总导航
- `docs/` 只承接相对稳定、相对正式的内容

## 当前目录

- `modules/`
  - 普通模块型笔记，如 `context / memory / session / group`
- `intent/`
  - intent 专题的稳定主入口
- `knowledge_construct/`
  - 知识库构建、爬取、落盘、目录组织专题
- `working/`
  - 中间态、临时方案、尚未稳定的文档
- `archives/`
  - 已经不在主线，但仍值得保留的历史材料

## 推荐阅读顺序

如果是第一次进入这个仓库，建议：

1. 先看 `../CONTEXT.md`
2. 再看本页，确认 `notes/` 的目录职责
3. 根据主题进入对应目录

建议入口：

- intent：`intent/README.md`
- knowledge construct：`knowledge_construct/README.md`
- context / memory / session / group：`modules/README.md`
- 过渡材料：`working/README.md`

## 放置规则

- 深度理解、阶段结论、过程知识：放 `notes/`
- 临时方案、草稿、尚未沉淀内容：放 `notes/working/`
- 已形成稳定共识、适合正式引用的内容：再考虑提炼到 `docs/`
- 明显过期但仍值得保留的材料：移到 `notes/archives/`

## 当前最简规则

现阶段优先遵守这 3 条：

1. 稳定主题入口文档留在对应主题目录
2. 过程性强、过渡性强的文档移入 `notes/working/`
3. 只有明显比 working note 更稳定的内容，才提炼到 `docs/`
