# 解释约束层

> status: historical
>
> note: 本文大量依赖旧的 `dependency_signals` 术语，现仅作历史参考；当前 `V2` 上下文主表达请优先看：
> - `context_signals`
> - `clarify_hint`
> - `ambiguity_states`
> - `missing_context_types`
>
> 入口：
> - [notes/intent/signal_info/README.md](/C:/Users/HUAWEI/PycharmProjects/Skill-First-Hybrid-RAG/notes/intent/signal_info/README.md)

## 1. 这一层是什么

解释约束层记录上下文和安全条件，用来影响业务信号如何被信任、约束和路由。

它不是规则命中层。

它也不是业务信号层。

它回答：

```text
这些信号在什么条件下成立？
是否能接上历史？
是否模糊？
为什么 unsupported？
```

## 2. 主要字段

当前字段：

- `dependency_signals`
- `context_signals`
- `unsupported_signals`

## 3. `dependency_signals`

`dependency_signals` 是旧式扁平上下文依赖字典。

当前 key：

- `none`
- `history_reference`
- `previous_answer`
- `previous_retrieval`
- `ambiguous`

### `none`

含义：

没有检测到上下文依赖。

注意：

- 通常是 fallback 状态。
- 它不是由某个具体 pattern 命中的。

### `history_reference`

含义：

query 引用了历史上下文。

典型来源：

- 有 history 时命中 `follow_up`。

例子：

```text
那这种情况呢？
```

### `previous_answer`

含义：

query 依赖上一轮 assistant 回答。

典型来源：

- 上一轮回答之后的 `ask_source`
- 上一轮回答之后的 `challenge`
- 上一轮回答之后的 `soft_doubt`

例子：

```text
你刚才为什么这么说？
```

### `previous_retrieval`

含义：

query 依赖上一轮检索上下文。

当前状态：

- schema 中保留。
- 当前规则流水线里还不是强使用字段。

### `ambiguous`

含义：

query 因为缺上下文或缺事实，直接回答有风险。

典型来源：

- follow-up 没有 history
- ask_source 没有 previous answer
- challenge-like query 没有 previous answer
- judgment query 太短，缺少足够事实

例子：

```text
那这个呢？
```

没有 history 时，这就是 ambiguous。

## 4. `ContextSignals`

`ContextSignals` 是新的强类型上下文对象。

它和 `dependency_signals` 有重叠，但更适合后续 resolver、模型和调试使用。

当前字段：

- `has_reference`
- `has_previous_intent`
- `has_implicit_history`
- `is_direct_followup`
- `previous_answer`
- `previous_retrieval`
- `ambiguous`
- `none`

### 和 `dependency_signals` 的关系

当前处于过渡期：

- `dependency_signals` 用于兼容旧逻辑、日志、旧测试和旧评估口径。
- `ContextSignals` 是未来更推荐的强类型视图。

它们不是两套独立事实。

它们是同一组上下文依赖信息的两种视图。

## 5. `unsupported_signals`

`unsupported_signals` 记录 unsupported 的细分原因码。

当前 key：

- `file_write_request`
- `file_delete_request`
- `kb_admin_request`
- `privileged_operation`
- `unknown_external_action`

这些不是顶层业务信号。

它们用于解释为什么 `safety` bucket 中出现了 `unsupported` / `out_of_scope`。

## 6. 为什么这一层看起来和 bucket 重复

确实存在主题重叠：

- `context bucket` 和 `ContextSignals` 都在讲上下文。
- `safety bucket` 和 `unsupported_signals` 都在讲不支持/拦截。

但职责不同。

## 7. Context Bucket vs Context State

`signal_buckets.context` 回答：

```text
出现了什么上下文语义信号？
```

例子：

- `follow_up`
- `ask_source`
- `challenge`
- `soft_doubt`
- `needs_clarification`

`ContextSignals` / `dependency_signals` 回答：

```text
这些上下文信号在什么条件下成立、变弱、模糊或可用？
```

例子：

- `previous_answer=True`
- `history_reference=True`
- `ambiguous=True`

例子：

```text
query: 你刚才为什么这么说？
```

如果有上一轮 assistant 回答：

```text
context bucket:
- ask_source

ContextSignals:
- previous_answer=True
```

如果没有上一轮 assistant 回答：

```text
context bucket:
- needs_clarification

ContextSignals:
- ambiguous=True
```

## 8. Safety Bucket vs Unsupported Reasons

`signal_buckets.safety` 回答：

```text
是否应该离开普通 QA？
```

例子：

- `unsupported`
- `out_of_scope`

`unsupported_signals` 回答：

```text
为什么 unsupported？
```

例子：

- `file_delete_request=True`
- `kb_admin_request=True`

## 9. 为什么不直接放进规则命中层

如果把所有上下文条件都编码进 rule id，规则会迅速膨胀。

不推荐方向：

```text
source.ask_basis.with_previous_answer
source.ask_basis.without_previous_answer_then_ambiguous
follow_up.reference.with_history
follow_up.reference.without_history
challenge.disagree.with_previous_answer
challenge.disagree.without_previous_answer
```

更清楚的方向：

```text
规则命中：
- source.ask_basis

业务信号：
- ask_source

解释约束：
- previous_answer=True 或 ambiguous=True
```

这样规则可复用，resolver/control 也可以在不同上下文下消费同一个业务信号。

## 10. 正确心智模型

解释约束层负责：

- 条件补充
- 稳定性判断
- 保守 gating
- 澄清/拒绝支持

可以说它在做“进一步筛选”，但更准确的说法是：

```text
对业务信号做条件筛选和稳定性约束。
```

