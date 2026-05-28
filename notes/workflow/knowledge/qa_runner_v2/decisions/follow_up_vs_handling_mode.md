# Follow Up Vs Handling Mode

## 当前结论

`follow_up` 当前不进入 `handling_mode`。

这条决策已经固定下来。

## 原因

`handling_mode` 表示的是：

- 当前这轮该按什么执行姿态处理

当前稳定 label space 是：

- `normal`
- `challenge`
- `clarify`
- `scope_info`
- `unsupported`

而 `follow_up` 表示的是：

- 当前 query 是否依赖前文
- 是否需要 context / target resolution / rewrite

因此它属于：

- intent
- context dependency
- context binding

维度，而不是 execution mode 维度。

## 为什么不能混

一条 query 可以同时是：

- `handling_mode = challenge`
- 并且 `follow_up = true`

例如：

- `你刚才第二点这个说法不对吧`

它既是：

- challenge

又是：

- follow-up

如果把 `follow_up` 硬塞进 `handling_mode`，会把两个维度压扁，导致表达能力下降。

## 当前生效方式

`follow_up` 当前通过这些信号间接生效：

- `use_context`
- `need_context_binding`
- `trace.context_dependency`
- `trace.ambiguity_states`
- `ContextBindingPower.query_style`

也就是说：

- `follow_up` 影响 binding / retrieval gate / route 内部执行
- 但不是 route-level handling mode
