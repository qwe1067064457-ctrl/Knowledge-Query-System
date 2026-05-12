# Intent 规则版 Confidence 说明

## 一、先说明一件事

当前规则版 `confidence` 不是统计意义上的真实概率。

它更准确地说，是：

> 当前规则证据是否足够强、足够一致、且被上下文支持，从而值得系统高置信地采用这个分流结果。

因此它本质上是：

- 工程决策强度

而不是：

- 校准过的真实概率

---

## 二、当前规则版 confidence 的来源

当前规则版 confidence 是通过规则先验强度映射出来的。

当前基础映射：

```python
RULE_STRENGTH_SCORES = {
    "high": 0.9,
    "medium": 0.6,
    "low": 0.3,
}
```

也就是说：

- `high -> 0.9`
- `medium -> 0.6`
- `low -> 0.3`

这里的 `score` 不是规则准确率，而是单条规则的人工先验权重。

---

## 三、规则版 confidence 不是怎么来的

不是这样来的：

- 不是模型打分
- 不是从数据自动学出来
- 不是某条规则历史 precision
- 不是某个 signal 的真实概率

它只是：

- 规则设计时对“这条规则有多强”的人工估计

---

## 四、当前一条规则如何带出 confidence

当前逻辑可以理解成：

```text
rule_id
  ↓
人工设定 strength
  ↓
固定映射出数值 score
```

例如：

- `challenge.disagree -> high -> 0.9`
- `source.ask_basis -> high -> 0.9`
- `context.follow_up.reference -> medium -> 0.6`

所以一条规则的 confidence 组成包括：

- `rule_id`
- `signal`
- `strength`
- `score`

示例：

```json
{
  "rule_id": "challenge.disagree",
  "signal": "challenge",
  "strength": "high",
  "score": 0.9
}
```

---

## 五、当前 signal 层 confidence 如何理解

一个 `signal` 下面可能有多条规则。

例如：

- `challenge.disagree`
- `challenge.confirmation`
- `challenge.soft_doubt`

都可能映射到：

- `signal = challenge`

因此：

- `strength` 应挂在 rule 层
- 不应直接挂在 signal 层

更合理的结构是：

```text
rule -> strength -> signal
```

不是：

```text
signal -> strength
```

---

## 六、如果只用规则计算 confidence，合理流程是什么

如果未来我们明确要用规则本身给出一个更完整的 confidence，可以按四步做。

## 第一步：单条规则基础分

用当前固定映射：

- `high = 0.9`
- `medium = 0.6`
- `low = 0.3`

## 第二步：同类 signal 聚合

如果多个规则支持同一 signal，可以聚合成一个 signal score。

第一版建议不要太复杂，先用简单策略：

```text
signal_score = max(rule_scores) + bonus
```

例如：

- 最高分是 `0.9`
- 如果还有第二条支持规则，加 `0.05`
- cap 到 `0.98`

也可以更严格地用概率式聚合：

```text
1 - Π(1 - rule_score_i)
```

但第一版不建议引入太重的公式。

## 第三步：冲突惩罚

如果同时出现互相冲突的信号，就应该降分。

例如：

- `qa` 和 `chat`
- `follow_up` 和 `needs_clarification`

这类情况下可以做：

```text
final_score = base_score - conflict_penalty
```

## 第四步：上下文修正

上下文状态可以进一步修正规则 confidence。

例如：

- `你确定吗？` + `has_previous_answer=true`
  - `challenge` 置信度上升
- `你确定吗？` + `has_previous_answer=false`
  - `challenge` 置信度应下降
  - 更适合 `needs_clarification`

最后可以再映射回离散级别：

- `>= 0.85 -> high`
- `0.6 ~ 0.84 -> medium`
- `< 0.6 -> low`

---

## 七、一个实际例子

用户 query：

```text
你刚才这个依据是什么，是不是不对？
```

命中规则：

- `challenge.disagree -> 0.9`
- `source.ask_basis -> 0.9`
- `context.follow_up.reference -> 0.6`

上下文状态：

- `has_previous_answer = true`

那么可以理解成：

- `challenge` 有强支持
- `ask_source` 有强支持
- `follow_up` 有中等支持
- 规则之间不冲突
- 上下文支持 `previous_answer`

因此 rule-based confidence 可以理解为：

- 最终决策强度较高

即：

```text
0.9+ 级别
```

再映射成：

- `high`

---

## 八、当前 confidence 应如何使用

当前更合理的用法是：

- 作为 `decision.strength`
- 用于 resolver / rule-model arbitration
- 用于解释性输出

不应直接把它当作：

- 规则真实准确率
- 统计意义上的置信概率

因此目前应该区分三件事：

### 1. `rule_design_strength`

规则设计时的先验强度。

例如：

- `high`
- `medium`
- `low`

### 2. `rule_score`

由先验强度映射出的数值权重。

例如：

- `0.9`
- `0.6`
- `0.3`

### 3. `rule_eval_precision / recall`

规则在真实数据上的表现。

这个必须靠评估数据跑出来，而不是手工设定。

---

## 九、我们当前已经明确的结论

### 1. strength 和规则准确率不能混

- `strength` 是先验
- `precision/recall` 是评估结果

### 2. signal 可以被多条规则支持

一个 query 完全可能同时命中：

- `challenge` 的高强规则
- `ask_source` 的高强规则
- `follow_up` 的中强规则

这不是问题，而是 evidence 层应允许的现象。

### 3. 同一条规则不会同时 high/medium/low

因为 strength 是规则设计属性，不是单次动态结果。

---

## 十、后续建议

当前这版已经有：

- `rule_id`
- `signal`
- `strength`
- `score`

后续应继续补：

- `tp`
- `fp`
- `fn`
- `precision`
- `recall`

这样以后才能明确地区分：

- 规则“看起来强”
- 和规则“真实有效”

---

## 十一、一句话总结

当前规则版 confidence 的本质是：

> 基于规则强度、规则一致性和上下文支持度得到的工程决策强度；它是 resolver 和路由决策的先验信号，不是规则真实准确率，后者必须通过评估数据单独验证。
