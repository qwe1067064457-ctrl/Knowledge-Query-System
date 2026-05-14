# Evidence 信号说明

## 1. 文档目标

这个目录专门说明 `intent` 模块里的 `evidence` 层。

它不只是列字段，而是要讲清楚：

- 哪些字段是具体规则命中
- 哪些字段是业务信号
- 哪些字段是上下文或安全约束
- 哪些字段是候选结果
- 为什么有些字段看起来重复，但职责并不一样

当你觉得 `evidence` 层“信号太多、太乱”时，优先看这个目录。

## 2. 推荐阅读顺序

1. [evidence_layer_model.md](./evidence_layer_model.md)
   - 解释四层模型：规则命中 -> 业务信号 -> 解释约束 -> 候选结果。

2. [business_signal_catalog.md](./business_signal_catalog.md)
   - 说明当前 `signal_buckets` 里的所有主干信号。

3. [explanatory_constraints.md](./explanatory_constraints.md)
   - 说明 `dependency_signals`、`ContextSignals`、`unsupported_signals`。
   - 解释它们为什么和 `context` / `safety` bucket 有主题重叠，但职责不同。

4. [candidate_intent_score.md](./candidate_intent_score.md)
   - 说明 `CandidateIntent.score` 是什么。
   - 说明它为什么不是 `rule_confidence`。

5. [confusing_signal_pairs.md](./confusing_signal_pairs.md)
   - 列出容易混淆的信号，并给出上下文对照例子。

6. [field_mapping.md](./field_mapping.md)
   - 按字段快速查它属于哪一层、承担什么职责。

## 3. 一句话模型

`evidence` 层可以这样读：

```text
规则命中层收集具体证据；
业务信号层把细规则归并成粗业务语义；
解释约束层说明这些信号在什么上下文或安全条件下成立；
候选结果层把这些信号聚合成 resolver 可消费的候选结论。
```

## 4. 关键术语

- 规则命中层：
  具体命中的规则，例如 `intent.qa.generic`、`intent.qa.judgment`、`challenge.disagree`、`context.follow_up.reference`。

- 业务信号层：
  `signal_buckets` 里的粗信号，例如 `qa`、`challenge`、`follow_up`、`complex`、`unsupported`。

- 解释约束层：
  上下文和安全条件，例如 `previous_answer`、`ambiguous`、`history_reference`、`file_delete_request`。

- 候选结果层：
  半收敛结果，例如 `CandidateIntent(qa, 0.85)`、`TaskCandidate(complex, verify, 0.8)`。

## 5. 当前设计提醒

`signal_buckets` 是主要的业务信号视图，但它不是最原子的层。

当前最接近“原子证据”的实现字段是 `matched_rules`。`signal_buckets` 已经是 `matched_rules` 之上的一层业务归并。

