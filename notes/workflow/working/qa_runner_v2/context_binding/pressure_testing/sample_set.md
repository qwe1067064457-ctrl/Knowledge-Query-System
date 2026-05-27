# Context Binding 压测样本集

## 说明

这份样本集用于 `Context Binding` 压测前的固定案例准备。

当前采用的压测策略是：

- 以当前线程近 20 轮真实对话样式为主样本来源
- 只保留少量必要的结构化补充样本
- 暂不继续大规模扩人工边界样本

这样做的原因是：

- 当前真实样式已经足够覆盖 `follow-up / challenge / standalone / memory-anchor` 主链
- 继续扩人工样本的边际收益开始下降
- 当前阶段更值得把精力放在真实样式压测与结果解读上

目标不是覆盖所有复杂语言现象，而是稳定覆盖当前最关键的 4 类场景：

1. follow-up
2. challenge
3. standalone
4. memory-anchor

每类至少保留：

- 1 个正例
- 1 个反例
- 1 个歧义例

## 当前样本使用原则

这份样本集现在主要承担两件事：

1. 给近 20 轮真实对话样式提供一个结构化映射
2. 补足真实对话中没有自然出现、但压测必须看的最小正反例

如果没有新的 blocker，后续不再主动扩大样本面。

## A. follow-up

### 正例

- query: `第二点展开讲讲`
- 预期：
  - `query_style = follow_up`
  - 规则直接命中单个 `answer_unit`
  - 不需要 fallback

### 反例

- query: `working memory 和 memory anchor 的区别是什么`
- 预期：
  - 不应强行按 follow-up 绑定
  - 更接近 standalone

### 歧义例

- query: `这个呢`
- 预期：
  - 如果 relevant set 中存在多个强候选，应返回 `needs_clarification`

## B. challenge

### 正例

- query: `你刚才说 challenge 还没完全统一，这个具体指什么`
- 预期：
  - `query_style = challenge`
  - relevant set 收到：
    - `answer_unit`
    - `review_outcome`
  - 大模型做 resolution

### 反例

- query: `好的，继续`
- 预期：
  - 不应抽成 `user_assertion`
  - 不应进入 challenge target 恢复

### 歧义例

- query: `这个说法有问题`
- 预期：
  - 如果存在多个 claim-like 候选，应优先走 clarification，而不是伪造唯一 target

### evidence 正例

- query: `你刚才说 challenge 还没完全统一，这个依据是什么`
- 预期：
  - `binding_result` 已经给出单个 target
  - `ChallengePower` 优先消费 binding contract
  - 如果 existing evidence 已足够，应直接 `success`
  - 不应触发 follow-up retrieval

### evidence 反例

- query: `你刚才说 challenge 还没完全统一，这个依据是什么`
- 预期：
  - `binding_result` 已经给出单个 target
  - existing evidence 不足时，允许触发 follow-up retrieval
  - 若补检索后仍不足，应返回 `insufficient_evidence`

## C. standalone

### 正例

- query: `working memory 和 memory anchor 的区别是什么`
- 预期：
  - query 自包含
  - 可以 `retrieve_on_raw_query` 或直接基于上下文回答

### 反例

- query: `第二点呢`
- 预期：
  - 不应按 standalone 处理

### 歧义例

- query: `这个具体是什么`
- 预期：
  - 如果上下文依赖明显但对象不清，应走 clarification

## D. memory-anchor

### 正例

- query: `如果 daily log 命中了之前那段讨论，它怎么参与 relevant pool`
- 预期：
  - memory anchor 可进入 relevant pool
  - 但不应被当作 working memory entry

### 反例

- query: `把刚才第二点说简单一点`
- 预期：
  - 没必要引入 memory anchor

### 歧义例

- query: `那个案例呢`
- 预期：
  - 如果 memory anchor 与 recent candidates 同时存在且无法稳定区分，应允许 clarification
