# Control Contract

## 1. 文档定位

这份文档是当前 `control` 层的正式 contract。

它回答四件事：

- `control` 到底输出什么
- 每个字段的职责与硬度是什么
- `route / handling_mode / capabilities / trace` 如何分工
- 哪些模糊边界继续交给 understanding 侧的小模型，而不是交给主回答模型临场决定

这份文档不负责描述具体 workflow 实现。

如果文档中的 contract 与历史样本、旧评估口径、兼容导出冲突：

- 以这份文档为准

## 2. 当前正式结构

当前 `control` 的正式主结构只有：

- `route`
- `handling_mode`
- `capabilities`
- `trace`

当前仍保留旧兼容导出：

- `mode`
- `rewrite`
- `force_citation`
- `use_planner`
- `decompose_query`
- `planning_level`

但这些字段的定位已经降级为：

- 兼容导出
- 历史观察口径
- 旧测试桥接字段

它们不是新的正式控制语义。

## 3. 字段职责与硬度

### 3.1 `route`

`route` 是执行入口的粗分流决定。

当前取值：

- `qa`
- `chat`
- `orchestrated`
- `reject`

它是：

- 硬约束

它回答的是：

- 这条请求进入哪类执行流

它不回答：

- 具体如何拆分步骤
- 是否先 planner
- 是否先 rewrite

### 3.2 `handling_mode`

`handling_mode` 是当前请求的主处理姿态。

当前取值：

- `normal`
- `clarify`
- `challenge`
- `scope_info`
- `unsupported`

它是：

- 较硬约束

它回答的是：

- 这条请求应该以什么交互姿态处理

它不回答：

- workflow 内部如何排步骤
- 要不要做 query rewrite
- 要不要做 planner

### 3.3 `capabilities`

`capabilities` 是后续执行流应尽量满足的粗能力约束。

当前只保留：

- `cite_sources`
- `use_context`

它是：

- 偏硬的软约束

它意味着：

- 默认应满足
- 如果 workflow 不满足，应有明确原因

它不是：

- 随便参考一下的建议
- 具体执行步骤清单

### 3.4 `trace`

`trace` 是 `resolved -> control` 的映射依据。

它负责：

- 给 workflow 提供必要理解输入
- 给评估与调试提供解释依据

它不是：

- 直接的 workflow 步骤定义

## 4. `route` 的正式判定 contract

### 4.1 核心定义

`route` 的判定标准不是：

- 这个请求复杂不复杂
- 有没有多个问号
- 有没有 follow-up

`route` 的判定标准是：

- 这条请求是否超出单轮回答流承载能力

### 4.2 什么叫“单轮回答流可承载”

满足下面条件时，应优先判为 `route=qa`：

- 请求虽然可能复杂，但仍可在一次回答组织中自然展开
- 不需要先确定阶段顺序，才能开始稳定回答
- 不需要先对子任务关系做显式编排，才能产出可靠结果
- 即使需要引用、上下文、结构化回答，也仍然主要是回答组织问题

典型仍应留在 `qa` 的情况：

- 简单问答
- 大多数 `compound`
- `follow_up`
- `ask_source`
- 普通上下文依赖
- `complex + summarize`

### 4.3 什么叫“必须先编排才能稳定处理”

满足下面条件时，应判为 `route=orchestrated`：

- 回答前必须先组织阶段、顺序或子任务关系
- 子任务关系本身就是处理对象的一部分
- 如果不先编排，回答会明显失稳、失真或混乱

当前第一版稳定进入条件：

- `task.topology == "staged"`
- `task.complexity == "complex"` 且 `task.shape in {"compare", "mixed", "verify"}`

### 4.4 哪些信号不应直接推入 `orchestrated`

下面这些本身不应直接决定 `route=orchestrated`：

- `ask_source`
- `follow_up`
- `challenge`
- `clarify_hint`
- 一般 `context_dependency`

这些只说明：

- 有引用要求
- 有上下文依赖
- 有质疑姿态
- 有理解缺口

它们不等于：

- 必须进入编排型执行流

## 5. `handling_mode` 的正式优先级 contract

### 5.1 单值原则

`handling_mode` 必须是单值主姿态。

原因是：

- 一个请求可以有多个修饰语义
- 但执行入口需要一个主导处理姿态

次级语义不应继续塞进多个 `handling_mode` 值，而应下沉到：

- `capabilities`
- `trace`

### 5.2 当前优先级

当前正式优先级是：

1. `unsupported`
2. `scope_info`
3. `clarify`
4. `challenge`
5. `normal`

对应含义：

- `unsupported`
  - 当前请求不应进入正常执行流
- `scope_info`
  - 当前请求主要在问能力、范围、边界
- `clarify`
  - 当前首要问题是理解缺口，而不是继续硬答
- `challenge`
  - 当前首要问题是针对前述内容的质疑/纠错姿态
- `normal`
  - 其余正常处理

### 5.3 组合语义的当前落法

#### `challenge + ask_source`

主姿态：

- `challenge`

次级要求：

- 通过 `capabilities=["cite_sources"]`

#### `clarify + ask_source`

主姿态：

- `clarify`

次级要求：

- 仍可保留 `cite_sources`
- 但前提是先承认当前缺目标或缺事实

#### `scope_info + follow_up`

主姿态：

- `scope_info`

次级要求：

- 如果后续要引用上文边界，则通过 `use_context`

#### `clarify + complex`

主姿态通常：

- `clarify`

例外：

- 如果当前请求本身已明显属于编排问题
- 且 `clarify_hint` 不能覆盖其主处理通道
- 则允许保住 `route=orchestrated`

也就是说：

- `handling_mode=clarify`
- 与
- `route=orchestrated`

可以共存

## 6. `capabilities` 的正式 contract

### 6.1 当前只保留两个 capability

- `cite_sources`
- `use_context`

当前不扩更多 capability。

### 6.2 `cite_sources`

表示：

- 后续执行流应尽量提供依据、出处、引用或证据锚点

触发来源通常包括：

- `modifiers.ask_source`
- `handling_mode=challenge`
- 默认 QA 引用要求

### 6.3 `use_context`

表示：

- 后续执行流不应把请求当成完全独立的新问题

触发来源通常包括：

- `context_dependency != none`
- `follow_up`
- 某些 challenge 场景对前文对象的显式依赖

### 6.4 硬度说明

`capabilities` 的硬度定义为：

- 默认应满足的软约束

如果 workflow 不满足：

- 应有明确原因

不建议把它理解成：

- 纯建议
- 绝对强制

## 7. `trace` 的 workflow contract

### 7.1 workflow 应读字段

后续 workflow 优先应读取这些字段：

- `main_intent`
- `modifiers`
- `task_complexity`
- `task_shape`
- `task_topology`
- `context_dependency`
- `ambiguity_states`
- `missing_context_types`

这些字段用于：

- 决定是否需要补上下文
- 决定是否需要内部编排
- 决定是否需要引用或承接前文

### 7.2 解释/调试字段

下面这些字段当前更偏解释与调试：

- `decision_strength`
- `decision_source`
- `decision_reason`

它们可以帮助：

- 评估回放
- 调试归因
- 错例分析

但不建议成为 workflow 的主执行判断输入。

## 8. 兼容字段退出 contract

### 8.1 当前允许的用途

当前兼容字段只允许用于：

- 兼容导出
- 历史观察
- 旧测试桥接

### 8.2 当前禁止的用途

当前不允许：

- 新逻辑依赖这些字段
- 新 workflow 入口依赖这些字段
- 继续围绕这些字段设计 `control`

### 8.3 退出顺序

建议退出顺序：

1. 文档降级  
2. 新代码禁止依赖  
3. workflow 切到消费新 contract  
4. 测试与评估口径迁移  
5. 正式删除兼容字段

## 9. 哪些灰区继续交给 SFT 小模型

下面这些问题仍然存在天然模糊性，不建议继续靠 rule 强扛，也不建议交给主回答模型临场决定：

### 9.1 `qa / orchestrated` 灰区

例如：

- `complex summarize`
- 带依赖的 `compound`
- `challenge + compare`
- `clarify + complex`

### 9.2 `handling_mode` 组合灰区

例如：

- `challenge + ask_source`
- `clarify + ask_source`
- `scope_info + history_reference`
- `soft_doubt + follow_up`

### 9.3 task 柔性边界

例如：

- `compare` 和 `mixed`
- `compound` 和 `complex`
- 回答结构要求和执行阶段要求之间的边界

### 9.4 ambiguity 强弱灰区

例如：

- `clarify_hint` 只是轻提示
- 还是已经强到不该直接答

这些更适合交给：

- understanding 侧的小模型
- SFT scorer
- learned boundary model

而不是交给主回答模型在生成阶段临场决定。

## 10. 当前结论

当前 `control` 层的正式设计结论是：

- `route`
  - 决定进入哪类执行流
- `handling_mode`
  - 决定主处理姿态
- `capabilities`
  - 决定默认应满足的粗能力约束
- `trace`
  - 提供 workflow 与调试所需的映射依据

也就是说：

- understanding 可以 `workflow-aware`
- `control` 可以执行流感知
- 但真正的执行策略仍属于 workflow
