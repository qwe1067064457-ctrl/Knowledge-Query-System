# Retrieval And Challenge

## 正式分层

- `retrieval_quality`
  - 检索层粗 gate
  - 回答：
    - 结果值不值得继续往后传
    - 是否要 repair
    - 是否命中太弱

- `evidence_check`
  - challenge / review 任务层 adjudication
  - 回答：
    - 当前证据是否足以支撑当前目标
    - 是否仍需要更多证据

## 什么时候检索

默认应检索：

- 法规 / 案例 / 文档事实型问题
- challenge / review
- compare / multi-query
- 命中 memory 摘要但摘要不足

可不检索：

- 纯改写 / 翻译 / 润色
- 纯会话型复述
- 当前窗口内就能完成且不依赖外部证据的问题

## Challenge 的正式角色

challenge 负责：

1. target resolution orchestration
2. evidence adjudication orchestration
3. answer constraints orchestration

challenge 内部允许补检索，但只能作为受控 follow-up retrieval。
