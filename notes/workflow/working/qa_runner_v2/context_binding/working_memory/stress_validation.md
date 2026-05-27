# Context Binding Working 记忆压测

## Goal

用当前线程近 20 轮对话验证 `QA Runner V2` 的 `context binding` 设计是否成立，并评估这 4 件事：

1. `relevant set` 是否足以支撑 follow-up / challenge / standalone 场景
2. `challenge target` 是否能先消费 existing evidence，再决定是否补检索
3. `Session Working Memory` 的写入规则是否能保住真正高价值对象
4. `fallback` 在歧义场景中是否合理

## 定位

这份文档属于：

- `context binding` 的 **working 记忆压测**
- 基于当前线程近 20 轮真实对话样式的验证记录

它不是正式稳定边界文档，不应放在 `notes/workflow/context_binding_v2/` 主专题下。

## 样本范围

本次验证使用当前线程中围绕以下主题连续展开的近 20 轮对话样式：

- `context binding` 应该是按需触发的 `query rewrite / context resolution`
- `Session Working Memory` 只保留高价值短程语义对象
- `Query Style` 与 `Handling Mode` 需要拆开
- `memory anchor` 是 long-term 命中后的上下文锚点，可进入 relevant pool
- `ChallengePower` 还未完全统一进同一套 V2 contract
- `fallback` 不能只是没找到，而要返回结构化降级动作

## 线程中应被保住的高价值对象

### focus_task

- 将 `context binding` 从 working 中间态收成正式专题
- 用 relevant set 驱动 follow-up / challenge / rewrite
- 把 `working memory / memory anchor / challenge` 边界写死

### answer_unit

- `context binding` 不是唯一 referent 恢复器，而是按需触发的 `query rewrite / context resolution`
- `Query Style` 和 `Handling Mode` 不是一回事
- `memory anchor` 可以进入 relevant pool，但不属于 working memory
- `ChallengePower` 还没完全统一进 Context Binding V2 contract
- 当前更适合内部验证，不适合直接生产放量

### user_assertion

- 旧 `dialogue_state focus candidate` 应该删掉
- relevant set 不追求唯一恢复 referent，而是先找到相关集
- 如果继续追求高鲁棒 relevant set，会明显进入高成本区
- 规则不能无限扩张，否则维护成本会持续抬升

### review_outcome

- `ContextBindingPower` 主链已经成立
- `relevant set` 仍然是规则第一版
- `working memory writer` 仍然偏粗
- `challenge` 尚未完全统一进同一合同

## 代表性 query 与预期表现

### Case 1: follow-up ordinal

query:

`第二点展开讲讲`

预期：

- `query_style = follow_up`
- `relevant set` 应缩到单个 `answer_unit`
- 规则应直接命中，不需要大模型
- 不需要 retrieval

当前评估：

- 这类显式序号 follow-up 已经相对稳定

### Case 2: challenge with weak explicit target

query:

`你刚才说 challenge 还没完全统一，这个具体指什么`

预期：

- `query_style = challenge`
- `relevant set` 应保留：
  - `answer_unit(challenge 未完全统一)`
  - `review_outcome(challenge 未统一)`
- 规则通常无法唯一命中
- 进入主大模型 resolution

当前评估：

- 这类 query 可以跑，但明显依赖大模型 resolution

### Case 3: pure ambiguity

query:

`这个呢`

预期：

- `query_style = follow_up`
- `relevant set` 可能留下多个强候选
- 若规则和大模型都不能稳定解析，应返回 `needs_clarification`

当前评估：

- 这是当前最合理的 fallback 场景之一

### Case 4: standalone architecture question

query:

`working memory 和 memory anchor 的区别是什么`

预期：

- `query_style = standalone`
- 即使 relevant set 为空，query 自身也足够完整
- 可以直接走 `retrieve_on_raw_query`，或由 answer side 直接回答

当前评估：

- 这类 query 不应强依赖 binding

### Case 5: memory anchor participation

query:

`如果 daily log 命中了之前那段讨论，它怎么参与 relevant pool`

预期：

- `memory_anchor` 可以进入 relevant pool
- 但它是 long-term context anchor，不是 working memory entry
- 后续更多由 challenge / hydrator / retrieval side 消费

当前评估：

- 当前 contract 是成立的

## challenge target 的实际评估

当前这 20 轮样式验证说明：

1. `challenge target` 的第一来源仍然主要是 `context binding` 的结果
2. `ChallengePower` 现在仍有一段自己的 target 识别与旧式 worker 路径
3. 所以 challenge 的消费链是成立的，但还没有完全和 `ContextBindingPower` 共用同一套 V2 resolution contract

本次结论：

- `challenge` 能先用 existing evidence 判断够不够
- 不够时再走 follow-up retrieval
- 但 target resolution 的统一性仍然是当前最大未完项之一

## working memory 写入的实际评估

当前 writer 能保住这些显式高价值对象：

- 总结性 answer unit
- 明确 challenge 的 user assertion
- 被采用的 resolved query
- 明确的 review status
- 明确 task hint

当前 writer 的主要问题：

- 容易漏掉不显式但后续确实会被追问的条目
- 也可能把看起来像结论、实际上只是过渡句的内容写进去

本次结论：

- writer 足以支撑第一版 relevant set
- 但还不足以支撑生产级高鲁棒相关集恢复

## fallback 的实际评估

当前线程样式下，最稳定的 fallback 是：

1. `needs_clarification`
2. `retrieve_on_raw_query`

语义上保留但尚未完全产品化的 fallback：

1. `rewrite_without_target`
2. `answer_from_context_only`

本次结论：

- 当前 fallback 机制足够支持内部验证
- 但不应夸大为完整的生产级降级体系

## 最终判断

基于这近 20 轮对话样式，`Context Binding V2` 的结论是：

1. 主思路成立：
   - `relevant pool -> relevant set -> 规则直出 / 大模型 resolution / fallback`
2. `Session Working Memory` 作为 short-term semantic candidate pool 是成立的
3. `memory anchor` 进入 relevant pool 的边界是清楚的
4. `challenge` 的 evidence-first 消费方向是成立的

但当前还不能宣称：

- 已经能稳定恢复复杂弱显式 referent
- 已经是生产级 relevant set retriever
- challenge 已完全统一进同一套 V2 contract

## 本轮 goal 结论

本轮 goal 已证明：

- `Context Binding V2` 足以支撑内部联调与灰度验证
- 不足以直接承诺生产级鲁棒恢复

下一步如果继续推进，优先级应是：

1. 把 `ChallengePower` 对齐到同一 contract
2. 稳住 `working memory writer` admission
3. 只做有限增强，不进入无限扩规则模式
