# CandidateIntent.score 说明

## 1. `CandidateIntent` 是什么

`CandidateIntent` 是主意图候选结果。

当前字段：

- `intent`
- `score`

它只覆盖 `MainIntent`：

- `qa`
- `chat`
- `system`
- `unsupported`

它不覆盖所有业务信号。

例如下面这些不是合法的 `CandidateIntent.intent`：

- `follow_up`
- `ask_source`
- `challenge`
- `soft_doubt`
- `needs_clarification`
- `complex`
- `multi_question`

这些分别属于 modifier、context signal、task signal 或 safety detail。

## 2. `CandidateIntent.score` 是什么

`CandidateIntent.score` 是启发式主意图候选分。

它不是：

- 统计概率
- `rule_confidence.final_score`
- 每个 raw signal 的分数
- 校准过的模型置信度

它是：

```text
resolver 在最终收敛 main_intent 前，用来排序和偏好的主意图候选分。
```

## 3. 当前给分逻辑

当前给分基于分支优先级和固定启发式分数。

### `unsupported -> 0.95`

如果命中 unsupported：

```text
CandidateIntent(unsupported, 0.95)
```

含义：

请求应强烈视为 unsupported。

其他普通候选会被压掉。

### `ask_capability -> system 0.95`

如果用户问系统能力：

```text
CandidateIntent(system, 0.95)
```

含义：

query 强烈偏向系统能力咨询。

### 强 QA 聚合 -> `qa 0.85`

如果出现下面任一项：

- `challenge`
- `ask_source`
- `soft_doubt`
- `follow_up`
- `domain_qa`
- `complex_task`
- `long_complex_fallback`

则：

```text
CandidateIntent(qa, 0.85)
```

含义：

很多非 `qa` 名称的信号，最终也会把主意图推向 `qa`。

例子：

- `ask_source` 不是主意图，但通常是在问知识依据。
- `follow_up` 不是主意图，但通常是在延续一个 QA 线程。
- `challenge` 不是主意图，但通常是在挑战上一轮 QA 回答。

### `multi_question -> qa 0.75 / chat 0.25`

如果 query 是多问，且不是明确 chat：

```text
CandidateIntent(qa, 0.75)
CandidateIntent(chat, 0.25)
```

含义：

系统主要把多问结构看成任务型 QA，但保留弱 chat 候选。

### `chat -> chat 0.9`

如果 query 明确是聊天：

```text
CandidateIntent(chat, 0.9)
```

### fallback -> `chat 0.55 / qa 0.45`

如果没有明显强信号：

```text
CandidateIntent(chat, 0.55)
CandidateIntent(qa, 0.45)
```

含义：

当前 fallback 稍微偏向 chat，但仍保留接近的 QA 可能性。

## 4. 为什么它只表示主意图

`CandidateIntent` 的职责是帮助 resolver 选择 `main_intent`。

其他维度有自己的位置：

- task 信息 -> `TaskCandidate`
- context dependency -> `ContextSignals` / `dependency_signals`
- unsupported 原因 -> `unsupported_signals`
- modifier -> 后续 `IntentModifiers`

所以不是每个 signal 都会变成 `CandidateIntent`。

例子：

```text
follow_up
```

它不应该变成：

```text
CandidateIntent(follow_up, 0.85)
```

它应该贡献给：

```text
CandidateIntent(qa, 0.85)
```

并在后续作为 modifier / context dependency 被保留。

## 5. 和 `rule_confidence` 的关系

`rule_confidence` 和 `CandidateIntent.score` 回答的问题不同。

`rule_confidence` 问：

```text
这个 signal 有多强？
```

`CandidateIntent.score` 问：

```text
这些 signals 最后把主意图推向哪里？
```

也就是：

- `rule_confidence` 是 signal 强度分。
- `CandidateIntent.score` 是主意图候选分。

## 6. 为什么 CandidateIntent 不直接使用 `rule_confidence`

当前设计把两者分开，因为 signal 强度和主意图聚合不是同一个计算问题。

例子：

```text
signals:
- ask_source
- previous_answer=True
```

`ask_source` 可能有很高的 signal confidence。

但主意图候选仍然是：

```text
qa
```

系统还需要一层映射：

```text
ask_source -> qa
follow_up -> qa
challenge -> qa
ask_capability -> system
unsupported -> unsupported
```

这个映射不是 `rule_confidence` 单独能提供的。

## 7. 未来更统一的形态

后续可以让 `CandidateIntent` 显式消费 `rule_confidence`：

```text
规则命中
-> signal confidence
-> signal-to-intent aggregation
-> CandidateIntent scores
-> resolver
```

这会更统一，但需要更清晰的 signal-to-intent 权重表。

当前设计更简单：

```text
rule_confidence 解释 signal 强度；
CandidateIntent 用启发式聚合主意图。
```

