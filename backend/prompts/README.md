# Prompt 管理

当前阶段只管理主问答链路的 `system prompt`。

## 文件

- `system_prompt.md`
  - 主问答助手的基础 system prompt

## 设计原则

- Prompt 文本放在文件中管理，不直接写死在业务代码里。
- Prompt 采用注入式设计：
  - 基础 system prompt 负责总行为约束
  - `ContextManager` 负责注入核心记忆、相关记忆、最近对话等上下文块
- 当前不拆分 router / planner / tool / critique 等其他 prompt。

## 路径配置

默认路径由 `backend/context/context_policy.json` 中的：

- `prompt.system_prompt_path`

控制。
