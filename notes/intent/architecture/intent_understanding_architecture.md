# Intent Understanding Architecture

## 1. 这篇文档讲什么

这篇文档只讲当前稳定的 understanding 架构，不讲：

- 具体 workflow 细节
- 训练实现细节
- 某一轮实验过程

它回答的是：

1. 当前主链怎么分层
2. 每层负责什么
3. 哪些事情不该在这一层做
4. 这套分层为什么能帮助后续模型接管

## 2. 当前主链

```text
input -> evidence -> resolved -> control
```

这是当前这条线最重要的总结构。

## 3. 各层职责

### 3.1 `input`

`input` 负责提供理解所需的输入材料。

当前典型包含：

- 当前用户 query
- 历史对话的结构化摘要
- `context_state`
- `model_context`

这一层不做判断，只做承载。

### 3.2 `evidence`

`evidence` 负责回答：

> 我们目前观察到了什么信号？

它允许：

- 多信号并存
- 候选冲突
- 不确定性共存

当前推荐理解成四类 evidence：

- `intent`
- `task`
- `context_fact`
- `safety`

它不应该直接做：

- 强执行承诺
- 最终 route 判定
- 最终 clarify 判定

### 3.3 `resolved`

`resolved` 负责回答：

> 当前请求最终被理解成什么？

当前稳定输出主要包括：

- `main_intent`
- `modifiers`
- `task.complexity`
- `task.shape`
- `task.topology`
- `context_dependency`
- `ambiguity_state`

这一层要做的是：

- 收敛
- 压缩多候选
- 形成稳定结构化结果

它不该直接做：

- `needs_query_decomposition`
- `needs_agent_planning`
- 过强的 workflow 预判

### 3.4 `control`

`control` 负责回答：

> 理解完之后，接下来粗分流怎么走？

它更接近工程映射层，当前长期目标是：

- `route`
- `handling_mode`
- `capabilities`
- `trace`

当前仍有兼容逻辑，是因为 understanding 层还在迁移。

## 4. 为什么要这样分层

### 4.1 把“看到了什么”和“最终理解成什么”分开

如果 `evidence` 和 `resolved` 混在一起，会出现两个问题：

1. 一些弱信号会被过早写成强结论
2. 后面很难分清是命中错了，还是收敛错了

所以：

- `evidence` 保留观察
- `resolved` 再做收敛

### 4.2 把“理解”与“执行”分开

过去最痛的点之一就是：

- rule 层过早替执行流做决定

例如：

- 把回答结构误判为 staged task
- 把模糊 query 直接强判成 clarify
- 把一些复杂度过早推成 `complex -> orchestrated`

现在分层的目的就是：

- understanding 先把问题理解好
- control 再做粗分流
- workflow 最后决定具体执行

## 5. 当前最关键的收缩方向

### 5.1 从强裁决改成候选态

一个重要方向是：

- `needs_clarification`
  - 不再是主设计里的强结论
  - 而是逐步转成：
    - `clarify_candidate`
    - `ambiguity_state`

### 5.2 从双角色 signal 改成职责拆分

过去有些 signal 同时表达：

- 请求语义
- 上下文依赖

现在目标是拆成：

- `request semantic`
- `context_fact`

### 5.3 从细粒度 rule 终判改成粗分类 / 粗识别

规则层继续保留：

- 粗分类
- 粗识别
- hard guard

但减少：

- 细 task 终判
- 强 clarify 裁决
- 强 decomposition 决策

## 6. 当前层间边界

### `evidence` 该做什么

- 收集 rule signal
- 收集 context fact
- 形成候选意图和候选任务
- 允许模糊、冲突、不确定

### `evidence` 不该做什么

- 不该直接下最终 route
- 不该直接决定 planner
- 不该把“可能需要澄清”直接写死成必须澄清

### `resolved` 该做什么

- 产出稳定结构
- 产出可消费的主标签
- 形成任务与上下文的统一解释

### `resolved` 不该做什么

- 不该直接产生细执行布尔开关
- 不该过早承诺 task 一定怎么执行

### `control` 该做什么

- 粗分流
- capability 开关
- trace

### `control` 不该做什么

- 重新理解 query
- 反向污染 understanding 层

## 7. 当前兼容态说明

当前并不是最终完成态，而是：

- 新结构已经进主链
- 旧字段仍有兼容影子

典型例子：

- `context_fact` 已经进入主设计
- 旧 `context` 桶还在部分兼容场景里出现

- `clarify_candidate / ambiguity_state` 已进入主链
- `needs_clarification` 仍作为兼容影子存在

这不是设计不清，而是迁移策略的一部分。

## 8. 一句话总结

当前 architecture 的核心不是“把更多判断塞进 rule 层”，而是：

> 用 `input -> evidence -> resolved -> control` 这条清晰主链，把理解、收敛、粗分流和后续执行解耦，从而让 rule 层变轻，让模型和 workflow 更容易在后面接管真正困难的部分。
