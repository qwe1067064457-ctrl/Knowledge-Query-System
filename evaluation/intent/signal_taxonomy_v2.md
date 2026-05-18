# Signal Taxonomy V2

`signal taxonomy` 只服务 `evidence` 层，不直接承担 `resolver` 或 `control` 的执行承诺。

## Buckets

- `intent`
  - 表示请求大类与意图修饰信号
  - 当前包含：`qa / chat / system / ask_capability / ask_source / challenge / soft_doubt`
- `task`
  - 表示任务结构与任务拓扑提示
  - 当前包含：`multi_question / parallel_subtasks / staged / complex`
- `context`
  - 表示上下文依赖与澄清相关信号
  - 当前包含：`follow_up / ask_source / challenge / soft_doubt / needs_clarification`
- `safety`
  - 表示越权、边界、拒绝类信号
  - 当前包含：`unsupported / out_of_scope`

## Rules

- 一个 signal 必须有主桶，不能把“只是命中”当成“多桶合法”。
- `intent` 负责“这类请求是什么”，不负责执行行为。
- `task` 负责“任务结构是什么”，不直接决定 `route`。
- `context` 负责“是否依赖历史或需要澄清”，不替代 `modifiers` 收敛。
- `safety` 负责“边界/风险”，不和普通 `qa` 信号混桶。

## Migration Notes

- `V1` 中的 `dependency_signals` 已被弱化，`V2` 以 typed `context_signals` 和 `signal_buckets` 为主。
- `signal migration quality` 重点检查：
  - 新 signal 是否异常暴增
  - 旧 signal 是否完成退场
  - bucket 归类是否稳定
  - 是否出现跨桶职责冲突
