# Route Layer

## 总体分层

`workflow` 当前通过 `route` 决定进入哪条执行流：

- `chat`
- `qa`
- `orchestrated`
- `reject`

这四条 route 的区别不是“最后是不是只回一段答案”，而是“回答之前要不要走受控执行准备链”。

## Chat Route

`chat` 的定位是：

- 轻对话响应流
- 不强调复杂 workflow
- 不以 retrieval / challenge / review 为默认主链

它适合：

- 系统能力说明
- 轻问答
- 不强依赖上下文和证据的自然响应

它不适合承载：

- 明显需要 retrieval 的知识型问题
- 需要 challenge / review 的争议点复审
- 多步执行组织

## QA Route

`qa` 的定位是：

- 受控单轮答复执行流
- 仍然是一轮回答
- 但允许在回答前按需挂接：
  - `context binding`
  - `retrieval gate`
  - `retrieval`
  - `retrieval quality`
  - `challenge / review`
  - `memory anchor -> hydrate`

它适合：

- 单问题知识问答
- 强上下文依赖的实现/状态问题
- 需要 evidence / fallback / uncertainty 控制的问题

## Orchestrated Route

`orchestrated` 的定位是：

- 多步执行编排流
- 比 `qa` 多一层显式执行组织

它通常会挂接：

- `planning`
- `decomposition`
- staged execution / checkpoint

它适合：

- 多子问题
- 需要显式分步组织的任务
- task topology 明显不是单问题的场景

## Reject Route

`reject` 的定位是：

- 拒绝 / 不支持流

它适合：

- unsupported
- 不安全或不该执行的请求

## 与 handling_mode 的关系

`route` 决定：

- 进入哪条执行流

`handling_mode` 决定：

- 这轮应该按什么执行姿态处理

当前 `handling_mode` 包括：

- `normal`
- `challenge`
- `clarify`
- `scope_info`
- `unsupported`

因此：

- `follow_up` 不是 route
- `follow_up` 也不是 handling mode
- `follow_up` 属于 intent / context / binding 维度
