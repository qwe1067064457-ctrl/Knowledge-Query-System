# Intent / Request Understanding 项目说明

## 1. 当前定位

这条线现在更准确的名字是：

- `Intent / Request Understanding`

它不是一个只做单标签分类的小模块，而是一条负责把用户请求理解清楚、为后续执行流提供稳定输入的主链。

它的目标不是：

- 直接回答问题
- 提前决定所有执行细节
- 用规则独自解决所有开放语义理解

它的目标是：

1. 判断请求大类
2. 识别关键修饰语义
3. 理解任务结构与上下文依赖
4. 拦住越权与高风险请求
5. 为后续 control / workflow 提供结构化输入

## 2. 为什么会从“意图识别”走到现在

最早这条线更接近传统 intent classifier：

- 识别 `qa / chat / system / unsupported`
- 再附带少量 modifier

但项目往前走之后，暴露了两个现实问题：

### 2.1 只有主意图不够

很多请求不是只靠单标签就能说明白，例如：

- `依据是什么？`
- `你确定吗？`
- `先说是否成立，再说依据，再说风险`
- `这种情况应该怎么分？`

这类请求还涉及：

- 上下文依赖
- 回答结构
- 任务复杂度
- 是否可能需要澄清

### 2.2 rule 层开始做得太多

旧问题不是规则不够多，而是规则承担了太多职责：

1. 基础识别
2. 任务理解
3. 上下文理解
4. 执行预判
5. 部分 workflow 决策

这会导致：

- 边界越来越模糊
- 调优成本越来越高
- 很多 query 难以归因到底是 rule 命中错、evidence 设计错、resolver 收敛错，还是 control 映射错

所以这条线后来明确转向：

- `rule-lite + model-centric understanding`

## 3. 当前架构摘要

当前主链是：

```text
input -> evidence -> resolved -> control
```

### `input`

负责承接：

- 当前用户 query
- 上下文状态
- 结构化历史信息

### `evidence`

负责收集：

- rule evidence
- context evidence
- task evidence
- safety evidence
- 可选 model evidence

### `resolved`

负责收敛成当前稳定理解结果：

- `main_intent`
- `modifiers`
- `task.complexity`
- `task.shape`
- `task.topology`
- `context_dependency`
- 可选 `ambiguity_state`

### `control`

负责粗分流与执行入口映射：

- `route`
- `handling_mode`
- `capabilities`
- `trace`

当前 control 还处于兼容态，最终会等 understanding 层彻底收稳后再系统收口。

## 4. 当前主设计方向

### 4.1 继续 `rule-lite`

rule 层继续保留：

- `unsupported / safety`
- `system / scope_question`
- `qa/chat/system/unsupported` 粗分类
- `follow_up / ask_source / challenge / soft_doubt` 粗识别
- baseline / teacher / regression anchor

rule 层逐步减少：

- 强 `clarify` 裁决
- 细粒度 task 终判
- 回答结构 vs 执行步骤终判
- 柔性 decomposition
- 过细 workflow 决策

### 4.2 引入中间状态，而不是强裁决

一个重要方向是：

- 能做候选，就不做终判
- 能做粗识别，就不做细裁决

典型例子：

- `needs_clarification`
  - 逐步下沉为
  - `clarify_candidate`
  - `ambiguity_state`

### 4.3 把“请求语义”和“上下文事实”拆开

我们现在不再希望同一个 signal 同时承担：

- 这是什么请求
- 它依赖什么上下文

所以主设计上开始拆成：

- `request semantic`
- `context_fact`

## 5. 当前主矛盾

目前 rule 层的问题，已经明确分成两类：

### 5.1 命中质量问题

例如：

- 某条规则该命中没命中
- 不该命中却命中了

这类主要看：

- precision
- recall
- f1
- required hit

### 5.2 设计问题

例如：

- signal 职责混杂
- bucket 设计不干净
- resolver 过早承诺复杂 task
- `clarify` 边界不稳
- `control` 过度依赖旧语义

这也是为什么当前不能只看“某条 rule 命中得准不准”，还必须看：

- evidence design
- resolver convergence
- distribution stability

## 6. 为什么要做 V1 / V2 双轨

这条线在重构时没有选择“一次性推翻”，而是用了双轨迁移：

- `V1`
  - 冻结旧口径
  - 继续做 baseline / teacher / regression anchor
- `V2`
  - 承接新的 signal taxonomy
  - 承接新的 evidence / resolver 边界
  - 用于迁移、对比和逐步替换

这样做的原因是：

1. 避免改一层就把训练、评估、导出全打断
2. 保留可比基线
3. 允许新旧语义并行观察

## 7. 当前已经完成了什么

当前已经落地的核心变化包括：

- `TaskTopology` 引入
- `mixed` 逻辑收紧
- `rule-lite` 方向冻结
- `V2 auto` 自动标注链路打通
- `V1 vs V2 auto` 差异报告
- `quality gate`
- `signal taxonomy` 收口到：
  - `intent`
  - `task`
  - `context_fact`
  - `safety`
- `clarify_candidate / ambiguity_state` 开始进入主链

## 8. 当前还没有完全收完的部分

还没最终落完的关键点包括：

- 双角色 signal 的彻底退场
- `clarify` 从旧强判定完全转到候选态
- `control v2` 正式重构
- 小模型真正接入中层理解
- `model_first_rule_guard` 的工程化落地

## 9. 一句话总结

当前 `intent` 这条线最合适的理解方式是：

> 一个从“rule-heavy 的意图识别器”逐步收缩为“rule-lite 的 request understanding 主链”的系统；它通过 `V1 / V2` 双轨迁移，把理解、评估、数据治理和后续模型接管统一到一个更清晰的架构里。
