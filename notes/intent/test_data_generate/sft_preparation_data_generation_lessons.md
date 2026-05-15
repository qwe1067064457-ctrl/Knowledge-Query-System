# Intent SFT 数据生成经验总结

## 1. 这份文档解决什么问题

这份文档专门总结：

- `intent` 小模型训练前，数据到底是怎么一层层生产出来的
- `campaign / 四层 draft / silver / gold / dev / heldout` 分别是什么意思
- 为什么我们明明有很多 `rule`、很多 `seed query`，最后真正可训练的数据却少很多
- 为什么后面必须从“手工抬 full gold”切到“分层数据工厂”

它不是规则说明书，也不是训练脚本说明书。

它更像：

> 面向 SFT 准备阶段的数据生产方法论总结。

---

## 2. 先区分几类数据

当前 `intent` 数据不是一类，而是多层：

1. `seed`
2. `campaign`
3. `four-layer draft`
4. `silver`
5. `gold`
6. `dev`
7. `frozen heldout`

如果不先把这几层分开，很容易出现两个误解：

- 误以为 `seed query` 很多，就等于训练集很多
- 误以为规则层生成了很多样本，就等于可以直接 SFT

实际上都不是。

---

## 3. `seed` 是什么

`seed` 是原料层。

典型例子：

- `evaluation/intent/query_inputs/intent_query_full_set.md`
- `evaluation/intent/query_inputs/seed_query_20260514.jsonl`
- `evaluation/intent/query_inputs/seed_query_20260515_router_augmented.jsonl`

它们的作用是：

- 提供原始 query 池
- 提供真实表达风格
- 提供后续扩展生成的入口

它们**不直接参与最终评估**，也**不直接等于训练集**。

一句话：

> `seed` 解决“原料从哪里来”，不解决“最终怎么训练”。

---

## 4. `campaign / 对抗草案` 是什么

`campaign` 是从 seed 或 query list 扩出来的一批样本草案目录。

它的特点是：

- 有批次语义
- 有历史变体
- 有边界压力
- 有对抗目标

它常见的生成方式包括：

- `supportive`
- `weak`
- `conflicting`
- `near_miss`
- `mixed`
- `cost_focused`

所以 `campaign` 更像：

> 一批已经过扩展生成和增强、但还没有进入最终训练层的候选样本池。

它常用于：

- 压规则
- 找 bad case
- 找边界
- 继续提升成 `silver` 或 `gold`

它不是最终 benchmark，也不该直接当最终 gold。

---

## 5. `four-layer draft` 是什么

`four-layer draft` 指的是：

- `input`
- `evidence`
- `resolved`
- `control`

这四层都先被预填成一个草稿。

要特别强调：

它不是只生成 `input.user_query` 草稿。

它是把整条链路先搭出来一个候选结构。

比如一条样本可能已经先被写成：

- `input.user_query`
- `input.history`
- `gold.evidence.required_signals`
- `gold.resolved.main_intent`
- `gold.resolved.task.shape`
- `gold.control.route`

但这时候它还只是 **draft**。

为什么叫 draft：

1. `history` 可能和 `user_query` 不一致
2. `evidence` 可能写多了或写偏了
3. `resolved.shape` 可能只是保底判断
4. `control.route / mode` 可能反映的是当前规则策略，而不是最终训练真值

一句话：

> `four-layer draft` 是“有结构的草稿”，不是最终真值。

---

## 6. `adversarial-intent-test-generator` 到底做什么

`adversarial-intent-test-generator` 不是只扩 seed query。

它更准确的角色是：

> 把 query 池、query list 或规则目标，扩成一批有攻击性的 `campaign` 和四层 draft。

它擅长做的是：

1. 扩展原始 query
2. 批量生成 `campaign`
3. 生成 `supportive / weak / conflicting / near_miss / mixed / cost_focused`
4. 预填四层 draft

它不擅长直接做的是：

1. 最终高可信 gold 裁决
2. 最终 `dev / heldout` 冻结
3. 完整替代人工校准

所以它是：

- **扩样器**
- **攻击集生成器**
- **四层草稿生成器**

不是最终真值生成器。

---

## 7. `auto-uplift` 是什么

`auto-uplift` 是我们后来补上的自动结构化提升步骤。

对应脚本：

- `evaluation/intent/auto_uplift_silver.py`

它做的事情是：

1. 吃一个 `campaign` 数据集目录
2. 逐条取出 `input.user_query` 和 `history`
3. 重新跑当前：
   - `classifier`
   - `resolver`
   - `control`
4. 忽略 campaign 里旧的 draft gold
5. 用**当前规则流水线**重新回填四层结构
6. 输出成新的 `silver` 数据集

输出样本会带：

- `label_tier = silver`
- `label_source = auto_uplift_rule_pipeline`
- `review_status = draft`

一句话：

> `auto-uplift` 是把 `campaign` 自动提升成可训练 `silver` 的工厂步骤。

---

## 8. `silver` 是什么

`silver` 是可训练层，不是 benchmark。

它和 gold 的关系不是“真假二选一”，而是“信任等级不同”。

### `silver` 的定位

- 可以进训练
- 不进最终 benchmark
- 默认可信度低于 gold
- 适合作为主扩量层

### 为什么现在必须用 silver

因为如果继续坚持：

- 所有训练样本都手工抬成 full gold

就会遇到三个问题：

1. 速度慢
2. token 消耗大
3. 训练样本永远起不来

所以 `silver` 的意义是：

> 让现有规则系统先充当自动标注器，把大量 campaign 快速转成可训练层。

当前正确的训练思路是：

- `gold`：高权重
- `silver`：主扩量
- `heldout`：只评估

---

## 9. `gold` 为什么贵

`gold` 依然是高成本层。

原因不是因为“模型不够聪明”，而是因为很多标签本身就带解释性和策略性：

- 这是 `soft_doubt` 还是普通 QA？
- 这是 `follow_up` 还是 `needs_clarification`？
- 这是 `verify` 还是 `mixed`？
- 这是 `rag` 还是 `direct`？

这些问题不能完全靠自动系统一次性保证正确。

所以即便是我们已经有：

- `campaign`
- `four-layer draft`
- `auto-uplift`

最终高可信 gold 仍然要靠人工控质。

更准确地说：

- AI 可以帮你降本
- 规则可以帮你提速
- 但最终边界裁决仍然贵

这也是为什么我们后面不能继续走：

> “所有训练样本都升成 gold”

而必须走：

> `seed -> campaign -> silver -> gold`

---

## 10. 为什么之前明明有 1000 多条，最后只有 100 多条训练样本

这正是前面最容易误解的地方。

问题不在于：

- 没有很多 `rule`
- 没有很多 `seed query`

问题在于：

> 原料很多，但能直接进入训练的高质量成品很少。

原因主要有四个：

1. `rule supervision` 主要是规则评估资产，不是完整训练样本
2. `campaign` 主要是增强池和压测池，不是最终训练集
3. `heldout / calibration` 不能直接混进 train
4. 把样本提升成高可信 gold 的产能太低

所以之前出现：

- 有 1000+ 原料
- 最后只有 100+ gold

不是因为“素材少”，而是因为：

> 从原料到 gold 的提升工序太贵、太慢。

---

## 11. 当前最合理的数据生产线

现在更合理的路线已经很清楚：

```text
seed / query_inputs
  -> adversarial-intent-test-generator
  -> campaign
  -> auto-uplift
  -> silver
  -> 人工挑关键边界
  -> gold
  -> 切 train / dev / frozen heldout
```

这条线的好处是：

1. 扩样快
2. token 成本可控
3. gold 只花在最值钱的地方
4. 训练集可以真正起量

---

## 12. 当前最重要的工程结论

### 12.1 `seed query` 不直接参与最终评估

这是现在必须明确冻结的原则。

`seed` 只在上游用来：

- 派生 campaign
- 做数据增强
- 做 candidate gold

不直接进最终 benchmark。

### 12.2 `campaign` 是增强池，不是最终真值

它的价值在于：

- 压边界
- 打规则
- 提供 uplift 原料

不是在于“直接拿来训最终模型”。

### 12.3 `silver` 是训练层，不是评估层

现在最现实的训练路线不是：

- 只靠少量 gold

而是：

- `gold + silver` 分层训练

### 12.4 `gold` 只保留给高价值边界

重点包括：

- `dev`
- `frozen heldout`
- 高风险标签
- 模糊边界
- 规则和模型最容易分歧的地方

---

## 13. 现在如果继续扩样，应该怎么做

不要再问“能不能一次性补齐所有最终 gold”。

更合理的问题应该是：

> 能不能一次性补齐到可训练规模？

答案是：可以。

做法应该是：

1. 批量生成 `campaign`
2. 批量 `auto-uplift` 成 `silver`
3. 只抽关键边界升级成 `gold`
4. 单独维护 `dev`
5. 单独冻结 `heldout`

这样你能一次性把：

- 训练量
- 扩展表达
- 规则覆盖

都拉起来，而不是继续把成本全压在 full gold 上。

---

## 14. 一句话总结

当前 `intent` 的 SFT 数据准备，已经从：

> “靠少量 seed + 手工抬 full gold”

转成了：

> “用 `adversarial-intent-test-generator` 扩 `campaign`，再用 `auto-uplift` 把 `campaign` 批量变成 `silver`，最后只把高价值边界升级成 `gold`。”

这就是当前最重要的数据生成经验。
