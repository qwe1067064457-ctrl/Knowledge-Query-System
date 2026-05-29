# binding prompts

## 职责

这里放 `orchestrated.binding` 层专属 prompt。

## 本质作用

这些文档的本质作用，是把 global binding framing 的判断口径外显出来，避免规则、模型和实现边界散落在代码里。

## 放什么

- global binding frame prompt

## 不放什么

- 不放 execution graph prompt
- 不放最终回答 prompt

## 与相邻层的边界

- 给 `GlobalBindingPromptHelper` 提供模板
- 不直接参与 deep binding 执行
