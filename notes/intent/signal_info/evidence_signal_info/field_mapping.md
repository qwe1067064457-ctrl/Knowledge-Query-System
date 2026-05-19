# Evidence 字段对照表

> status: reference
>
> note: 本文中的字段映射表包含历史字段与旧兼容表达；当前 `V2` 正式 schema 以代码和下面两份入口文档为准：
> - [notes/intent/signal_info/README.md](/C:/Users/HUAWEI/PycharmProjects/Skill-First-Hybrid-RAG/notes/intent/signal_info/README.md)
> - [notes/intent/signal_info/evidence_signal_info/README.md](/C:/Users/HUAWEI/PycharmProjects/Skill-First-Hybrid-RAG/notes/intent/signal_info/evidence_signal_info/README.md)

## 1. 快速表

| 字段 | 所属层 | 回答的问题 | 是否规则级 | 是否业务信号 | 是否候选结果 |
| --- | --- | --- | --- | --- | --- |
| `matched_rules` | 规则命中层 | 具体哪些规则命中了？ | 是 | 否 | 否 |
| `raw_signals` | 兼容/调试扁平视图 | 哪些 bucket signal 出现过？ | 否 | 是，但已扁平化 | 否 |
| `signal_buckets.intent` | 业务信号层 | 出现了什么意图类信号？ | 否 | 是 | 否 |
| `signal_buckets.task` | 业务信号层 | 出现了什么任务类信号？ | 否 | 是 | 否 |
| `signal_buckets.context` | 业务信号层 | 出现了什么上下文语义信号？ | 否 | 是 | 否 |
| `signal_buckets.safety` | 业务信号层 | 出现了什么安全/拦截信号？ | 否 | 是 | 否 |
| `dependency_signals` | 解释约束层 | 有什么上下文依赖条件？ | 否 | 否 | 否 |
| `context_signals` | 解释约束层 | 上下文依赖条件的强类型视图 | 否 | 否 | 否 |
| `unsupported_signals` | 解释约束层 | 为什么 unsupported？ | 否 | 否 | 否 |
| `candidate_intents` | 候选结果层 | 哪些主意图候选更可能？ | 否 | 否 | 是 |
| `task_candidates` | 候选结果层 | 哪些任务复杂度/shape 更可能？ | 否 | 否 | 是 |
| `rule_confidence` | 信号强度解释 | 规则信号有多强？ | 从规则派生 | 否 | 否 |
| `model_result` | 模型证据层 | 模型产出了什么 evidence？ | 否 | 取决于模型输出 | 取决于模型输出 |

## 2. `matched_rules`

这是最具体的规则证据。

例子：

```json
{
  "rule_id": "intent.qa.generic",
  "signal": "qa",
  "strength": "medium",
  "score": 0.6
}
```

理解为：

```text
泛 QA 这条具体规则命中了，并产生了 qa 证据。
```

## 3. `signal_buckets`

这是主要业务信号视图。

例子：

```json
{
  "intent": ["qa", "ask_source"],
  "task": ["complex"],
  "context": ["ask_source"],
  "safety": []
}
```

理解为：

```text
query 有 QA / 问来源语义，是复杂任务，并且可能依赖上下文。
```

## 4. `raw_signals`

这是 `signal_buckets` 的扁平兼容视图。

用途：

- 旧测试
- 旧评估脚本
- `rule_confidence`
- 快速 debug 日志

新阅读和新设计优先看：

```text
signal_buckets
```

## 5. `dependency_signals` 和 `ContextSignals`

它们不是独立业务语义。

它们是条件状态。

例子：

```json
{
  "previous_answer": true,
  "ambiguous": false
}
```

理解为：

```text
query 可以接到上一轮回答，并且当前没有被视为模糊。
```

## 6. `unsupported_signals`

它解释 `unsupported`。

例子：

```json
{
  "file_delete_request": true,
  "kb_admin_request": false
}
```

理解为：

```text
请求 unsupported 的原因是用户要求删除文件。
```

## 7. `candidate_intents`

它只表示主意图候选。

例子：

```json
[
  {"intent": "qa", "score": 0.85}
]
```

理解为：

```text
综合当前 evidence，主意图强烈倾向 qa。
```

不要理解为：

```text
所有 signal 都在这里被打分。
```

## 8. `task_candidates`

它表示任务层候选。

例子：

```json
[
  {"complexity": "complex", "shape": "verify", "score": 0.8}
]
```

理解为：

```text
任务大概率是复杂任务，并且更像 verify 形态。
```

## 9. `rule_confidence`

`rule_confidence` 解释 signal 强度。

它和 `CandidateIntent.score` 分开。

区分方式：

```text
rule_confidence: 这个 signal 有多强？
CandidateIntent.score: 这些 signal 把主意图推向哪里？
```

