# Intent 规则版 Confidence 说明

## 1. 文档目标

这份文档用于说明当前 `intent` 模块中的规则版 `confidence` 是什么、怎么算、当前代码已经实现了什么，以及它和真实规则准确率之间的边界。

当前规则版 `confidence` 的目标不是给出统计概率，而是给出：

> 当前规则证据是否足够强、足够一致、且被上下文支持，从而值得系统较高置信地采用这个规则分流结果。

所以它本质上是：

- 工程决策强度

而不是：

- 校准过的真实概率
- 某条规则的历史 precision
- 某个 signal 的真实命中概率

---

## 2. 它解决什么问题

如果只看“命中了哪些规则”，我们很难区分下面几种情况：

- 命中了一条非常强的规则
- 命中了两条都支持同一 signal 的规则
- 命中了互相冲突的规则
- 命中了某条规则，但上下文并不支持

规则版 `confidence` 的作用，就是把这些信息收束成一个更稳定的工程信号，用在：

- `evidence` 层的解释输出
- resolver 的 `decision.strength` 辅助
- `rule_only / rule_plus_model / model_first_with_rule_guard` 的策略参考

---

## 3. 当前实现位置

当前实现位于：

- [C:\Users\HUAWEI\PycharmProjects\Skill-First-Hybrid-RAG\backend\intent\rule_confidence.py](/C:/Users/HUAWEI/PycharmProjects/Skill-First-Hybrid-RAG/backend/intent/rule_confidence.py)

结果结构定义位于：

- [C:\Users\HUAWEI\PycharmProjects\Skill-First-Hybrid-RAG\backend\intent\types.py](/C:/Users/HUAWEI/PycharmProjects/Skill-First-Hybrid-RAG/backend/intent/types.py)

当前会被挂到：

- `IntentEvidence.rule_confidence`

并且在 resolver 中作为 `decision.strength` 的参考之一。

---

## 4. 当前规则版 confidence 的四步公式

当前实现采用四步：

```text
单条规则基础分
  ↓
同类 signal 聚合
  ↓
冲突惩罚
  ↓
上下文修正
  ↓
得到每个 signal 的 final_score
  ↓
选出 final_signal / final_score / final_level
```

下面逐项说明。

---

## 5. 第一步：单条规则基础分

### 5.1 基础思想

每条规则在设计时会先被赋予一个 `strength`：

- `high`
- `medium`
- `low`

然后再映射成一个固定基础分数 `score`。

### 5.2 当前固定映射

当前约定是：

```text
high   -> 0.9
medium -> 0.6
low    -> 0.3
```

这意味着：

- `strength` 是规则设计阶段给出的先验强度
- `score` 是先验强度映射出的数值权重

这里的 `score` 不是规则真实准确率。

### 5.3 当前结构如何理解

一条命中规则的数据可以理解成：

```json
{
  "rule_id": "challenge.disagree",
  "signal": "challenge",
  "strength": "high",
  "score": 0.9
}
```

这表示：

- 命中了哪条规则
- 这条规则支持哪个标准化 signal
- 这条规则在设计上被认为有多强
- 它带来的基础数值权重是多少

---

## 6. 第二步：同类 signal 聚合

### 6.1 为什么要聚合

一个 signal 可能由多条规则共同支持。

例如 `challenge` 可能同时被这些规则支持：

- `challenge.disagree`
- `challenge.confirmation`
- `challenge.soft_doubt`

因此规则版 `confidence` 不是直接对单条规则打结论，而是先按 `signal` 分组。

### 6.2 当前聚合方式

当前对每个 signal 的基础分采用：

```text
base_score = 同组规则中的最大 score
```

也就是说：

- 如果一个 signal 下有多条规则，先取其中最强的一条作为基础分

### 6.3 当前 support bonus

如果同一个 signal 下有多条规则支持，会追加 `support bonus`：

```text
rule_count <= 1 -> 0.00
第 2 条支持规则 -> +0.05
第 3 条及以上 -> 总 bonus 最多 +0.10
```

当前公式等价于：

```text
support_bonus = min(0.05 * (rule_count - 1), 0.1)
```

例如：

- 1 条规则支持：`+0.00`
- 2 条规则支持：`+0.05`
- 3 条规则支持：`+0.10`
- 4 条规则支持：仍然 `+0.10`

这样做的含义是：

- 多条规则共同支持同一 signal，会提升其证据强度
- 但这个提升是有上限的，避免简单叠加导致分数过高

---

## 7. 第三步：冲突惩罚

### 7.1 为什么需要冲突惩罚

如果一个 query 同时命中了互相冲突的 signal，那么单靠基础分和 bonus 会过于乐观。

例如：

- `qa` 和 `chat`
- `follow_up` 和 `needs_clarification`
- `challenge` 和 `needs_clarification`

这类情况说明规则证据不干净，需要降分。

### 7.2 当前冲突矩阵

当前实现中的主要冲突关系是：

```text
qa         vs chat/system/unsupported
chat       vs qa/system/unsupported
system     vs qa/chat
follow_up  vs needs_clarification
challenge  vs needs_clarification
ask_source vs needs_clarification
```

### 7.3 当前惩罚分值

当前代码里的惩罚强度是：

```text
qa vs chat              -> 0.20
qa vs system            -> 0.15
qa vs unsupported       -> 0.20
chat vs qa              -> 0.20
chat vs system          -> 0.15
chat vs unsupported     -> 0.20
system vs qa            -> 0.15
system vs chat          -> 0.15
follow_up vs clarify    -> 0.10
challenge vs clarify    -> 0.20
ask_source vs clarify   -> 0.10
```

### 7.4 当前计算方式

如果某个 signal 的冲突对手也在当前 `raw_signals` 中激活，就把对应惩罚累计起来：

```text
conflict_penalty = sum(active conflicting penalties)
```

这意味着冲突越多，分数越低。

---

## 8. 第四步：上下文修正

### 8.1 为什么需要上下文修正

有些规则看 query 文本本身会像某个 signal，但如果没有合适的上下文，它其实不该高置信命中。

例如：

- “你确定吗？”只有在存在上一轮回答时，才是强 `challenge`
- “那这个呢？”只有在存在上下文时，才更像 `follow_up`

所以规则版 `confidence` 会引入 `context_state` 和 `dependency_signals` 做修正。

### 8.2 当前支持的上下文修正规则

#### `challenge`

```text
has_previous_answer = true  -> +0.10
否则                        -> -0.30
```

含义：

- 有上一轮回答时，challenge 更可信
- 没有上一轮回答时，challenge 大幅降分

#### `ask_source`

```text
has_previous_answer = true  -> +0.05
dependency ambiguous = true -> -0.20
否则                        -> 0.00
```

含义：

- 有上一轮回答时，“依据是什么”更像在追问证据
- 如果上下文模糊，`ask_source` 不应过高

#### `follow_up`

```text
has_history = true                     -> +0.05
且 last_main_intent = qa               -> 再 +0.05
或 dependency history_reference = true -> 再 +0.05
无 history                             -> -0.20
```

含义：

- 有历史时，`follow_up` 更可信
- 如果上一轮本来就是 `qa`，或 evidence 里明确有 `history_reference`，再加一档
- 没有历史时，`follow_up` 要降分

#### `needs_clarification`

```text
dependency ambiguous = true -> +0.10
```

含义：

- 如果 evidence 已经判断上下文模糊，澄清需求更可信

#### `qa`

```text
last_main_intent = qa -> +0.05
```

含义：

- 如果上一轮主意图就是 `qa`，当前仍然偏 `qa` 会更可信一些

---

## 9. 当前总公式

对每个 signal，当前计算方式可以写成：

```text
final_score =
  clamp(
    base_score
    + support_bonus
    - conflict_penalty
    + context_adjustment
  )
```

其中：

- `base_score`：同 signal 内最高规则分
- `support_bonus`：多条规则共同支持带来的加分
- `conflict_penalty`：和其他 active signal 冲突带来的减分
- `context_adjustment`：上下文对 signal 的加减分
- `clamp`：把最终结果限制在 `[0.0, 0.98]`

也就是说，当前最终分不会超过 `0.98`。

---

## 10. 当前 `final_level` 的映射

当前分数会进一步映射成离散等级：

```text
score >= 0.85 -> high
score >= 0.60 -> medium
否则           -> low
```

这个等级是当前 resolver 更容易使用的工程输出。

它代表：

- `high`：规则证据强、相对一致、且上下文支持
- `medium`：有一定支持，但还存在模糊性或冲突
- `low`：证据较弱，不应过度相信

---

## 11. 当前输出结构

当前规则版 `confidence` 最终产出的是一个 `RuleConfidence`。

核心字段包括：

- `signal_confidences`
  - 每个 signal 的详细分数结构
- `final_signal`
  - 当前分数最高的 signal
- `final_score`
  - 当前分数最高 signal 的最终分
- `final_level`
  - `high / medium / low`
- `explanation`
  - 可读解释文本

其中每个 `SignalConfidence` 包括：

- `signal`
- `base_score`
- `support_bonus`
- `conflict_penalty`
- `context_adjustment`
- `final_score`
- `level`
- `supporting_rule_ids`

这意味着当前实现已经可以解释：

- 哪个 signal 最终最强
- 为什么它最强
- 哪些规则在支持它
- 它是否因为冲突或上下文被拉低

---

## 12. 一个完整示例

用户输入：

```text
你刚才这个依据是什么，是不是不对？
```

假设命中了这些规则：

- `challenge.disagree -> signal=challenge -> score=0.9`
- `source.ask_basis -> signal=ask_source -> score=0.9`
- `context.follow_up.reference -> signal=follow_up -> score=0.6`

并且上下文状态为：

- `has_history = true`
- `has_previous_answer = true`

则可以这样理解：

### `challenge`

- 基础分：`0.9`
- 同类 bonus：`0.0`
- 冲突惩罚：`0.0`
- 上下文修正：`+0.1`
- 最终分：`0.98`（经过 cap）

### `ask_source`

- 基础分：`0.9`
- 同类 bonus：`0.0`
- 冲突惩罚：`0.0`
- 上下文修正：`+0.05`
- 最终分：`0.95`

### `follow_up`

- 基础分：`0.6`
- 同类 bonus：`0.0`
- 冲突惩罚：`0.0`
- 上下文修正：正向
- 最终分：中等偏高

因此最终大概率会得到：

- `final_signal = challenge`
- `final_level = high`

这不是说 challenge 一定真实正确，而是说：

> 从规则证据强度上看，当前最值得系统采用的主导规则信号是 challenge。

---

## 13. 当前测试覆盖了什么

当前规则版 `confidence` 的单元测试位于：

- [C:\Users\HUAWEI\PycharmProjects\Skill-First-Hybrid-RAG\backend_test\intent\test_rule_confidence.py](/C:/Users/HUAWEI/PycharmProjects/Skill-First-Hybrid-RAG/backend_test/intent/test_rule_confidence.py)

当前已覆盖：

### 分类 1：单条高强规则

- 验证单条高强规则在上下文支持下能保持高置信

### 分类 2：同类 signal bonus

- 验证多条规则支持同一 signal 时，会增加 `support_bonus`

### 分类 3：冲突惩罚

- 验证 `qa` 与 `chat` 同时命中时，会出现 `conflict_penalty`

### 分类 4：上下文缺失降分

- 验证没有历史时，`follow_up` 的 `context_adjustment` 为负

也就是说，当前测试覆盖的是：

> 规则版 confidence 的计算逻辑是否按设计执行。

而不是：

> 它是否已经被真实数据证明足够准确。

---

## 14. 它和真实规则准确率的关系

这一点需要明确区分。

当前规则版 `confidence` 只能说明：

- 当前规则证据强不强
- 当前规则证据是否一致
- 当前上下文是否支持该信号

它不能说明：

- 这条规则真实 precision 是多少
- 这条规则真实 recall 是多少
- 这个 signal 在真实用户数据里有多大概率成立

因此必须区分三件事：

### 14.1 `rule_design_strength`

规则设计时给定的先验强度：

- `high`
- `medium`
- `low`

### 14.2 `rule_score`

由先验强度映射出的数值：

- `0.9`
- `0.6`
- `0.3`

### 14.3 `rule_eval_precision / recall`

规则在真实标注数据上的表现。

这一部分必须通过：

- `tp`
- `fp`
- `fn`
- `precision`
- `recall`

去单独评估，而不是靠 `confidence` 推出来。

---

## 15. 当前边界和后续建议

### 15.1 当前边界

当前规则版 `confidence` 已经可用，但它的边界也很清楚：

- 是工程决策强度，不是真实概率
- 可以帮助 resolver，但不能替代规则评估
- 可以增强 explainability，但不能直接证明规则质量

### 15.2 后续建议

后续建议沿两条线继续补：

#### 线 1：继续补计算逻辑测试

例如：

- 更多冲突组合
- 更多上下文修正场景
- 多 signal 并存时的排序稳定性

#### 线 2：补真实规则评估

在 `evaluation/intent/` 中补齐：

- `tp`
- `fp`
- `fn`
- `precision`
- `recall`

这样以后就能清楚区分：

- 哪条规则“看起来强”
- 哪条规则“真实有效”

---

## 16. 一句话总结

当前规则版 `confidence` 的本质是：

> 基于单条规则基础分、同类 signal 聚合、冲突惩罚和上下文修正得到的工程决策强度；它服务于 evidence 解释和 resolver 辅助，不等于规则真实准确率，后者必须通过独立评估数据验证。
