# Control Signal V2 说明

## 1. 当前已落地的定位

当前 `control` 的职责正式收口为：

- `route`
- `handling_mode`
- `capabilities`
- `trace`

它继续消费 `resolved`，但不再直接承担过细的执行裁决。

当前仍然保留了一层兼容导出，用于承接旧测试与旧观察口径：

- `mode`
- `rewrite`
- `force_citation`
- `use_planner`
- `decompose_query`
- `planning_level`

这些字段现在属于：

- 兼容视图
- 派生结果

而不是新的正式控制主结构。

## 2. 当前正式边界

### `route`

当前正式粗分流为：

- `qa`
- `chat`
- `orchestrated`
- `reject`

其中：

- `qa`
  - 仍可由单轮回答流承载
- `orchestrated`
  - 已明显更像编排问题，而不是普通回答组织问题
- `reject`
  - 不进入正常执行流

### `handling_mode`

当前主处理姿态为单值：

- `normal`
- `clarify`
- `challenge`
- `scope_info`
- `unsupported`

它回答的是：

- 这条请求应该以什么交互姿态处理

它不回答：

- 要不要 planner
- 要不要拆 query
- 要不要 rewrite

### `capabilities`

当前正式只收两个粗提示：

- `cite_sources`
- `use_context`

它们只表达：

- 是否需要显式带依据/出处
- 是否需要显式消费历史/上下文依赖

它们不等于 workflow 步骤。

### `trace`

`trace` 负责保留 `resolved -> control` 映射依据，当前主要挂：

- `main_intent`
- `modifiers`
- `task_complexity`
- `task_shape`
- `task_topology`
- `context_dependency`
- `ambiguity_states`
- `missing_context_types`
- `decision_strength`
- `decision_source`
- `decision_reason`

它的作用是：

- 给 workflow 后续消费
- 给调试与评估解释

## 3. 当前映射原则

### 什么会推动 `route=orchestrated`

当前只在这些情况进入 `orchestrated`：

- `task.topology == "staged"`
- `task.complexity == "complex"` 且 `task.shape in {"compare", "mixed", "verify"}`

另外有一个保守兜底：

- 如果当前是 `clarify_hint`
- 但任务本身已经是复杂 `verify / compare / mixed`
- 则优先保住 `orchestrated`

### 什么仍然留在 `route=qa`

下面这些情况当前仍优先留在 `qa`：

- 简单问答
- 大多数 `compound`
- `follow_up`
- `ask_source`
- 一般上下文依赖
- 复杂但仍可按单轮回答组织的请求，例如 `complex + summarize`

### `handling_mode` 如何收敛

当前映射原则是：

- `unsupported` / `out_of_scope` -> `unsupported`
- `ask_capability` / `system` -> `scope_info`
- `challenge` -> `challenge`
- `clarify_hint` -> `clarify`
- 其余 -> `normal`

这里强调：

- `handling_mode` 是主姿态，单值
- `capabilities` 是附加提示，可多值

## 4. 当前没有放进 control 正式结构的内容

下面这些没有删除，也没有失效：

- `task.complexity`
- `task.shape`
- `task.topology`
- `ambiguity_state`
- `context_dependency`

它们仍然稳定存在于 `resolved` 和 `control.trace` 中。

只是当前不再由 `control` 直接翻译成：

- `planner`
- `decompose`
- `rewrite`

原因是：

- 这些已经属于 workflow 执行策略
- 不应再由 control 过早强裁决

## 5. 当前 control 与 workflow 的边界

当前建议严格保持：

- `resolved`
  - 负责把请求理解清楚
- `control`
  - 负责粗分流 + 主姿态 + 粗能力提示
- `workflow`
  - 负责具体执行策略

也就是说：

- understanding 可以 `workflow-aware`
- 但不应 `workflow-deciding`

## 6. 当前仍属未来工作

这次落地还没有做的事包括：

- 把真正的 workflow 消费口径正式接到 `control v2`
- 去掉所有旧兼容字段
- 在评估导出里统一迁掉旧的 `route=rag/direct/agent` 历史样本口径

所以当前最准确的状态是：

- `control v2` 已完成最小落地
- 但全链路迁移仍处于兼容过渡期
