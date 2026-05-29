# Orchestrated Execution Layer

## 它做什么

`orchestrated execution layer` 负责：

- 执行 `ExecutionGraph`
- 推进 unit 状态机
- 调 capability executor
- 收口 `rich execution result`

## 它更本质地解决什么问题

它的本质作用不是“执行几个 worker”，而是把多步任务变成：

- 可追踪
- 可状态化
- 可被 answer layer 和其他后续层稳定消费

的中间执行结果。

如果没有这层，后续 owner 只能消费一段自然语言，很难稳定知道：

- 哪个 unit 完成了
- 哪个 unit 降级了
- 哪个 branch 被跳过
- 是否还能继续推进

## 当前 owner 结构

- `backend/workflow/orchestrated/execution_layer/engine/`
- `backend/workflow/orchestrated/execution_layer/executors/`
- `backend/workflow/orchestrated/execution_layer/contracts/`
- `backend/workflow/orchestrated/execution_layer/helpers/`

## 与相邻层的边界

- 上游：
  - `planning` 给 `ExecutionGraph`
- 下游：
  - route 收口为 `ExecutionPayload`
  - `answer_layer` 从 rich execution result / payload 中做 answer-facing 重组
