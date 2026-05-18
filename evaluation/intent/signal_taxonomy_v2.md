# Signal Taxonomy V2

`signal taxonomy` 只服务 `evidence` 层，不直接承担 `resolver` 或 `control` 的执行承诺。

## Buckets

- `intent`
  - 表示请求大类与请求语义
  - 当前包含：`qa / chat / system / ask_capability / scope_question / follow_up / ask_source / challenge / soft_doubt`
- `task`
  - 表示任务结构与任务拓扑提示
  - 当前包含：`multi_question / parallel_subtasks / staged / complex`
- `context_fact`
  - 表示理解当前请求所依赖的上下文事实
  - 当前包含：`history_reference / needs_previous_answer / previous_retrieval / missing_reference_target / possibly_ambiguous / needs_context_check`
- `safety`
  - 表示越权、边界、拒绝类信号
  - 当前包含：`unsupported / out_of_scope`

## Rules

- 一个 signal 必须先有主职责，再讨论兼容别名。
- `intent` 负责“这是什么请求”，不直接表达缺不缺上下文。
- `task` 负责“任务结构是什么”，不直接决定 `route`。
- `context_fact` 只负责“理解当前请求依赖什么上下文事实”，不承担请求语义。
- `safety` 负责“边界/风险”，不和普通 `qa` 信号混桶。

## Compatibility

- 旧导出与旧代码里的 `context` 在 `V2` 口径下统一按 `context_fact` 理解。
- `ask_capability` 仍保留作兼容字段，逐步收敛到 `scope_question`。
- `needs_clarification` 仍保留作兼容结果，逐步收敛到 `clarify_candidate / ambiguity_state`。

## Migration Notes

- `V1` 中的 `dependency_signals` 已被弱化，`V2` 以 typed `context_signals` 和 `signal_buckets.context_fact` 为主。
- `signal migration quality` 重点检查：
  - 新 signal 是否异常暴增
  - 旧 signal 是否完成退场
  - bucket 归类是否稳定
  - 是否继续出现请求语义与上下文事实混桶
- `V2` 主口径不再接受双角色 signal：
  - `ask_source / challenge / soft_doubt` 只能作为 `intent` 语义信号出现
  - 如果理解依赖上下文，应额外落为 `context_fact`
    - 例如 `needs_previous_answer / missing_reference_target / possibly_ambiguous`
