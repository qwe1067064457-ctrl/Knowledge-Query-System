# Execution Layer Rules

- `execution_layer` 负责 unit 执行、状态流转、rich execution result。
- 它不是最终回答层，也不是 workflow transport 总包。
- `planner` 只给图和 unit contract，不拥有状态机。
- `execution_layer` 默认状态：
  - `pending`
  - `completed`
  - `skipped`
  - `degraded`
  - `blocked`
