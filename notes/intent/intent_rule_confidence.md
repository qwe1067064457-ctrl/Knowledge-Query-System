# Intent Rule Confidence 说明

## 1. 一句话定义

`rule_confidence` 的唯一职责，是评估：

- **当前这组 rule evidence 到底可不可信**

它不是校准过的真实概率，也不是最终决策器。  
它更像一个：

- 规则证据可信度评审器

## 2. 它不是什么

`rule_confidence` 不是：

- 最终 `main_intent`
- 最终 `route`
- workflow 决策器
- planner 开关
- 某条规则历史 precision 的替代品

它只回答一件事：

- 这份规则证据是否足够强、足够一致、足够被上下文支持，值得 resolver 更放心地采信

## 3. 它为什么存在

如果只看“命中了哪些规则”，会混在一起：

- 命中了一条很强的规则
- 命中了多条共同支持同一 signal 的规则
- 命中了彼此冲突的规则
- 命中了规则，但上下文其实不支持

`rule_confidence` 的价值就是把这些情况收成一个更稳定的工程判断。

## 4. 当前它怎么判断“可不可信”

当前实现主要看四件事：

1. 单条规则基础强度
- `high / medium / low`

2. 同类支持
- 同一个 signal 是否被多条规则共同支持

3. 冲突惩罚
- 是否同时命中了互相冲突的 signal

4. 上下文修正
- 当前上下文是否支持这个 signal 继续成立

所以它本质上是在回答：

- 规则证据强不强
- 规则证据干不干净
- 规则证据有没有被上下文打脸

## 5. 当前输出是什么

`rule_confidence` 不是只给一个总分。

它更接近：

1. 先给每个 signal 的可信度结果
2. 再收出一个最终摘要

当前可以这样理解：

- 细分评估：
  - 每个 signal 的最终得分
- 总体评估：
  - `final_signal`
  - `final_score`
  - `final_level`

也就是说：

- 有逐项判断
- 也有总体摘要

## 6. 它和 candidate 的关系

不要把 `rule_confidence` 和 `candidate score` 混在一起。

两者不一样：

### `candidate score`

回答的是：

- 哪些高层语义对象值得交给 resolver 收敛

例如：

- `candidate_intents`
- `task_candidates`

### `rule_confidence`

回答的是：

- 当前整组 rule evidence 值不值得信

所以：

- `candidate` 是收敛对象
- `confidence` 是证据质量评估

它们会相关，但不是同一个维度。

## 7. 当前代码位置

实现位置：

- [backend/intent/rule_confidence.py](/C:/Users/HUAWEI/PycharmProjects/Skill-First-Hybrid-RAG/backend/intent/rule_confidence.py)

类型位置：

- [backend/intent/types.py](/C:/Users/HUAWEI/PycharmProjects/Skill-First-Hybrid-RAG/backend/intent/types.py)

当前结果会挂到：

- `IntentEvidence.rule_confidence`

## 8. 当前使用边界

当前推荐把它当成：

- evidence 的辅助解释结果
- resolver 的辅助判断依据
- 规则系统回归与调优的质量刻度

不建议把它当成：

- 模型概率替代
- 单独的路由器
- 全链路执行策略判断器

## 9. 当前这份文档该怎么用

如果你关心的是：

- 为什么这次规则命中了，但系统仍不该太自信
- 为什么有些 signal 同时出现时要更保守
- 为什么 `context` 会影响 rule 证据强弱

先看这份文档就够了。

如果你关心的是：

- `evidence` 里到底有哪些正式字段
- `signal_buckets`、`candidate_intents`、`context_signals` 怎么分

请先看：

- [signal_info/README.md](/C:/Users/HUAWEI/PycharmProjects/Skill-First-Hybrid-RAG/notes/intent/signal_info/README.md)
