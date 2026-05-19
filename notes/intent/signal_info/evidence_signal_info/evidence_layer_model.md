# Evidence 四层模型

> status: historical
>
> note: 本文描述的是旧的 evidence 分层视角，不再是当前正式主轴；当前 `V2` 只保留一套正式语义分类：
> - `intent`
> - `task`
> - `context`
> - `safety`
>
> 请优先看：
> - [notes/intent/signal_info/README.md](/C:/Users/HUAWEI/PycharmProjects/Skill-First-Hybrid-RAG/notes/intent/signal_info/README.md)
> - [notes/intent/signal_info/evidence_signal_info/README.md](/C:/Users/HUAWEI/PycharmProjects/Skill-First-Hybrid-RAG/notes/intent/signal_info/evidence_signal_info/README.md)

## 1. 为什么需要四层模型

`evidence` 对象里同时放了几类不同性质的信息。

如果把所有字段都叫成“signal”，会很难理解。更清楚的方式是拆成四层：

```text
规则命中层
-> 业务信号层
-> 解释约束层
-> 候选结果层
```

每一层回答的问题不同。

## 2. 第一层：规则命中层

回答的问题：

```text
具体是哪条规则看到了什么？
```

主要字段：

- `matched_rules`

典型例子：

- `intent.qa.generic`
- `intent.qa.judgment`
- `intent.qa.domain`
- `source.ask_basis`
- `challenge.disagree`
- `challenge.soft_doubt`
- `context.follow_up.reference`
- `context.follow_up.missing_history`
- `task.enumerated_questions`
- `task.complex.request`
- `unsupported.file_delete_request`

这一层最接近正则和规则命中。

例子：

```text
query: 如果公司拖欠工资，我可以怎么处理？

规则命中：
- intent.qa.generic
```

这只说明“泛 QA 规则命中了”，还没有说明最终主意图一定如何收敛。

## 3. 第二层：业务信号层

回答的问题：

```text
这些具体规则在业务上说明了什么？
```

主要字段：

- `signal_buckets`

例子：

- `intent.qa.generic` -> `qa`
- `intent.qa.judgment` -> `qa`
- `challenge.disagree` -> `challenge`
- `challenge.soft_doubt` -> `soft_doubt`
- `context.follow_up.reference` -> `follow_up`
- `task.enumerated_questions` -> `multi_question`
- `task.complex.request` -> `complex`
- `unsupported.file_delete_request` -> `unsupported` + `out_of_scope`

这一层是粗粒度业务归并层。

可以这样理解：

```text
规则命中层 -> 业务信号层
= 细分规则证据 -> 粗业务语义
```

这一步已经有“收敛”的思想，但它还不是最终 resolver 决策。

## 4. 第三层：解释约束层

回答的问题：

```text
这些业务信号在什么上下文或安全条件下成立？
```

主要字段：

- `dependency_signals`
- `context_signals`
- `unsupported_signals`

例子：

- `previous_answer=True`
- `history_reference=True`
- `ambiguous=True`
- `file_delete_request=True`
- `kb_admin_request=True`

这一层不是 `signal_buckets.context` 或 `signal_buckets.safety` 的简单重复。

它补的是条件信息：

- 这个信号是否依赖上一轮回答
- 这个 follow-up 是否能接上历史
- 当前 query 是否因为缺上下文而模糊
- unsupported 到底是哪一种不支持

例子：

```text
query: 你刚才为什么这么说？

规则命中：
- source.ask_basis

业务信号：
- ask_source

解释约束：
- 如果有上一轮 assistant 回答，则 previous_answer=True
- 如果没有上一轮回答，且 query 不能自洽，则 ambiguous=True
```

同一个 `ask_source`，会因为解释约束不同而走向不同的后续处理。

## 5. 第四层：候选结果层

回答的问题：

```text
综合业务信号和约束后，resolver 应该优先考虑哪些候选结论？
```

主要字段：

- `candidate_intents`
- `task_candidates`

例子：

- `CandidateIntent(intent="qa", score=0.85)`
- `CandidateIntent(intent="system", score=0.95)`
- `TaskCandidate(complexity="compound", shape="multi_question", score=0.9)`
- `TaskCandidate(complexity="complex", shape="verify", score=0.8)`

候选结果不是原始 signal。

它们是半收敛结果，用来降低 resolver 的处理成本。

## 6. 完整例子

Query:

```text
这样算医疗事故吗？
```

可能的 evidence 流程：

```text
规则命中层：
- intent.qa.judgment

业务信号层：
- intent: qa

解释约束层：
- 如果 query 太短且缺少事实，可能 ambiguous=True

候选结果层：
- CandidateIntent(qa, 0.85)
- TaskCandidate(simple, single_question, 0.8)
```

重点：

`ambiguous=True` 不等于 `qa` 不成立。

它表达的是：

```text
这大概率是 QA，但当前信息可能不足，需要先澄清。
```

## 7. 正确短公式

推荐使用：

```text
规则先命中；
信号再归并；
上下文和安全再约束；
候选再准备收敛。
```

不要使用：

```text
evidence 里的所有字段都是同一种 signal。
```

