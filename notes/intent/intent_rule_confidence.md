# Intent Rule Confidence

## 1. 这篇文档的边界

这篇文档只讲：

- rule 命中层面的 confidence
- signal / candidate 侧的置信调整

它不代表：

- evidence 设计质量
- resolver 收敛质量
- control 映射质量
- 整个 understanding 主链的最终正确性

也就是说：

- `rule confidence` 很重要
- 但它不是总质量分

## 2. 为什么还需要 rule confidence

即使我们在继续推进 `rule-lite`，规则层仍然要承担：

- hard guard
- coarse classification
- coarse recognition
- baseline / teacher

因此 rule 层仍然需要一套可解释的 confidence 机制，帮助回答：

1. 为什么这条 rule 被认为足够强
2. 为什么某个 candidate 比另一个 candidate 更可信
3. 为什么当前结果应该进入 `rule_only`
4. 为什么应该交给后续 model 辅助

## 3. 当前 confidence 的作用

当前 rule confidence 更适合拿来支持这些事情：

### 3.1 局部命中解释

例如：

- 哪些 rule 命中了
- 哪些是 required hit
- 哪些是 support bonus

### 3.2 candidate 排序

例如：

- `qa` 和 `chat` 都有弱信号时
- 哪个 candidate 更值得保留为主候选

### 3.3 模式切换

例如：

- 当前是否足够进入 `rule_only`
- 还是更适合 `rule_plus_model`

## 4. 当前不该把它拿来做什么

### 4.1 不能直接代表 resolver 正确

即使某条 rule confidence 很高，也不代表：

- `main_intent` 收得一定对
- `complexity` 一定收得对
- `clarify` 一定判得对

### 4.2 不能直接代表 evidence 设计正确

某个 signal 即使命中很稳，也可能：

- 职责混杂
- bucket 放错
- 在系统里承担了不该承担的语义

### 4.3 不能直接代表 control 应该怎么走

control 是消费 `resolved` 的，而不是直接消费某条 rule confidence。

## 5. 当前推荐理解方式

我建议把 rule confidence 理解成：

> 规则层对“当前命中与候选排序”的局部置信解释系统

而不是：

> 整条 understanding 主链的统一信心分数

## 6. 和当前问题分类的关系

当前 rule 层问题被分成：

1. `命中质量问题`
2. `设计问题`

`rule confidence` 主要服务第 1 类，也就是：

- 规则命中质量
- 候选冲突解释
- required hit 稳定性

它对第 2 类问题只能间接提供线索，不能直接裁决。

## 7. 在 V2 里的角色

进入 `V2` 以后，rule confidence 的角色并没有消失，反而更明确：

- 它继续服务 rule baseline
- 服务 teacher 标签
- 服务 regression anchor
- 服务 `rule_only / rule_plus_model` 模式判断

但它不会再被误当成：

- “整个系统已经足够确定”

## 8. 一句话总结

当前 `rule confidence` 最合适的定位是：

> 一个用于解释 rule 命中、candidate 排序和 coarse understanding 稳定性的局部置信系统，而不是整个 understanding 主链的总质量指标。
