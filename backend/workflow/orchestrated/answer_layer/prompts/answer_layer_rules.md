# Answer Layer Rules

- `answer_layer` 负责把 rich execution result 重组为 answer-facing 结果。
- 它不是 graph 执行层。
- 它不是最终 system prompt 组装层。
- 它要做的是低损失重组，不是二次薄压缩。
