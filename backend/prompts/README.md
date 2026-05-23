# Prompt 管理

这个目录只存放 prompt 文本与规则说明，不存放 prompt 组装逻辑。

## 子目录

- `system/`
  - 主回答模型的基础系统提示词与运行时统一覆盖规则
- `classifiers/`
  - 分类器或路由器使用的 prompt
- `workflow/`
  - workflow 结果如何影响主回答行为与结果投影的规则说明

## 设计原则

- Prompt 文本放在 markdown 文件中管理，不直接写死在业务代码里。
- Prompt 装配逻辑放在 `backend/graph/prompt_builders/`。
- `ContextManager` 只负责准备上下文材料，不负责拥有最终主回答 prompt。

## 路径配置

默认主回答 system prompt 路径由 `backend/context/context_policy.json` 中的：

- `prompt.system_prompt_path`

控制。
