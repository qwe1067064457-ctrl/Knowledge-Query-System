# answer_layer prompts

## 职责

这里放 answer layer 的提示词和规则文档。

## 本质作用

这些文档的本质作用，是把 answer-facing 重组逻辑外显化：它不是做薄压缩，而是降噪、保关键、重组顺序。

## 放什么

- answer layer assembler prompt
- answer layer rules
- answer layer projection rules

## 不放什么

- 不放最终主回答系统 prompt
- 不放 graph runtime 规则

## 与相邻层的边界

- 给 answer layer owner 提供文档化约束
- shared prompt mapping 只负责最终文本组装
