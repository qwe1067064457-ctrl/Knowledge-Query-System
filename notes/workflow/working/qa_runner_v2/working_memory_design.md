# QA Runner V2 Working Memory Design

## 目标

这份文件只回答三个问题：

1. `session working memory` 到底存什么
2. 存的时候怎样保证高价值、低噪音
3. 新 query 到来时，规则到底怎么命中候选，再怎样交给小模型做最终 resolution

这里的 working memory 是：

- `session-scoped`
- `short-term`
- `semantic`
- 服务 `binding` 和 `challenge`

它不是：

- 长程 memory
- `daily_log`
- `domain_case`
- 大而全的 `session metadata dict`

---

## 存储格式

建议从当前 metadata 字段升级成：

```text
sessions/
  session_xxx.jsonl
  session_xxx.meta.json
  session_xxx.working_memory.jsonl
  session_xxx.working_memory.head.json
```

含义：

- `session_xxx.working_memory.jsonl`
  - 逐条存 working memory entry
  - 适合 append
  - 适合筛选
- `session_xxx.working_memory.head.json`
  - 存当前快速读取所需的小快照
  - 例如最近 entry ids、当前任务、最新 rewritten query

---

## 只存 5 类 entry

第一版建议只存这 5 类，不要一下子扩太多。

### 1. `focus_task`

表示当前正在推进的任务。

例如：

- 核验“试用期结论是否成立”
- 比较 A 和 B 的规定差异

### 2. `resolved_query`

表示某轮 query rewrite / resolution 的结果。

例如：

- 原 query
- rewritten query
- 当前轮解析出的 target ids

### 3. `answer_unit`

表示主回答中的一个可被后续引用的回答单元。

注意：

- 第一版先不上正式 `claim`
- 先上更轻的 `answer_unit`

例如：

- 第 1 点结论
- 第 2 点结论
- 某一段明确判断

### 4. `user_assertion`

表示用户 query 中自带的陈述。

例如：

- “你之前没有用到这个指标”
- “这个条款不适用于这里”

这类对象对 `challenge` 特别重要。

### 5. `review_outcome`

表示上一轮 challenge / review 的关键结论。

例如：

- 哪个对象已支持
- 哪个对象证据不足
- 哪个对象需要继续补检索

---

## entry 最小 schema

```json
{
  "entry_id": "wm_001",
  "entry_type": "answer_unit",
  "turn_id": "turn_12",
  "source_kind": "answer|user_query|review|binding",
  "source_ref": "answer_turn_12_unit_2",
  "content": "一年期劳动合同试用期上限为一个月",
  "structured_payload": {},
  "confidence": "high",
  "status": "active",
  "created_at": "2026-05-25T10:00:00+08:00"
}
```

### 字段意义

- `entry_id`
  - working memory 内唯一 id
- `entry_type`
  - 这条记忆属于哪一类
- `turn_id`
  - 产生于哪轮
- `source_kind`
  - 来源类型
- `source_ref`
  - 原始对象引用，后面可用于回锚
- `content`
  - 给筛选与 LLM 消费的主文本
- `structured_payload`
  - 结构化补充字段
- `confidence`
  - `high|medium|low`
- `status`
  - `active|superseded|stale`
- `created_at`
  - 写入时间

---

## 5 类 entry 的示例

### `focus_task`

```json
{
  "entry_id": "wm_task_001",
  "entry_type": "focus_task",
  "turn_id": "turn_18",
  "source_kind": "user_query",
  "source_ref": "turn_18_user",
  "content": "核验一年期劳动合同试用期上限结论是否成立",
  "structured_payload": {
    "task_kind": "challenge_validation",
    "topic": "试用期上限"
  },
  "confidence": "high",
  "status": "active",
  "created_at": "2026-05-25T10:00:00+08:00"
}
```

### `resolved_query`

```json
{
  "entry_id": "wm_query_003",
  "entry_type": "resolved_query",
  "turn_id": "turn_19",
  "source_kind": "binding",
  "source_ref": "binding_turn_19",
  "content": "一年期劳动合同试用期上限是多少",
  "structured_payload": {
    "original_query": "那这个上限呢",
    "resolved_target_ids": ["wm_answer_002"],
    "rewrite_reason": "follow_up_pronoun_resolution"
  },
  "confidence": "high",
  "status": "active",
  "created_at": "2026-05-25T10:01:00+08:00"
}
```

### `answer_unit`

```json
{
  "entry_id": "wm_answer_002",
  "entry_type": "answer_unit",
  "turn_id": "turn_17",
  "source_kind": "answer",
  "source_ref": "answer_turn_17_unit_2",
  "content": "一年期劳动合同试用期上限为一个月",
  "structured_payload": {
    "unit_index": 2,
    "topic": "试用期上限",
    "evidence_refs": ["evidence_19"]
  },
  "confidence": "high",
  "status": "active",
  "created_at": "2026-05-25T09:58:00+08:00"
}
```

### `user_assertion`

```json
{
  "entry_id": "wm_assert_001",
  "entry_type": "user_assertion",
  "turn_id": "turn_20",
  "source_kind": "user_query",
  "source_ref": "turn_20_user",
  "content": "你刚才没有处理试用期例外",
  "structured_payload": {
    "assertion_kind": "missing_consideration",
    "topic": "试用期例外"
  },
  "confidence": "high",
  "status": "active",
  "created_at": "2026-05-25T10:02:00+08:00"
}
```

### `review_outcome`

```json
{
  "entry_id": "wm_review_004",
  "entry_type": "review_outcome",
  "turn_id": "turn_21",
  "source_kind": "review",
  "source_ref": "review_turn_21",
  "content": "关于试用期上限的结论已有直接证据支持，但关于例外情形证据不足",
  "structured_payload": {
    "supported_target_ids": ["wm_answer_002"],
    "insufficient_target_ids": ["wm_assert_001"],
    "review_status": "partial_success"
  },
  "confidence": "high",
  "status": "active",
  "created_at": "2026-05-25T10:03:00+08:00"
}
```

---

## 高精度存储原则

### 1. 只存高价值 entry

不要把所有中间态都写进去。

应优先写入：

- 后续可能被引用的回答单元
- 当前轮真正被采用的 rewritten query
- 用户明确提出的 challenge/assertion
- challenge/review 的关键结论
- 当前活跃任务

不建议写入：

- 临时规则命中痕迹
- 低置信猜测
- 大段重复上下文
- 纯调试信息

### 2. 只有过 admission gate 才能写入

建议 admission gate 只问这 4 个问题：

1. 这条信息后续会不会被引用
2. 这条信息有没有明确来源
3. 这条信息是否高于低置信猜测
4. 这条信息是否能帮助后续 `binding` 或 `challenge`

四个问题里至少满足前 3 个，才入 working memory。

### 3. 必须允许 supersede

working memory 不是事实库，而是短程执行记忆。

所以：

- 新的 `resolved_query` 可以替代旧的
- 新的 `review_outcome` 可以覆盖旧结论

建议用：

- `status=active`
- `status=superseded`

来做状态管理。

---

## 规则到底怎么命中

规则不做最终 target 判定。

规则只做：

- 高精度缩候选
- 便宜预筛
- 降低 LLM 消耗

### 规则筛选总链路

```text
working_memory entries
-> 时间窗口筛
-> 类型筛
-> 显式模式筛
-> confidence / status 筛
-> 候选压到 3~5 条
-> 必要时交给小模型做最终 resolution
```

---

## 第一步：时间窗口筛

规则：

- 默认只看最近 `3~5` 轮
- 或最近 `8~12` 条 active entries

命中目的：

- 把长历史噪音先砍掉

示例：

- 当前 query 来自 `turn_22`
- 先只看 `turn_17 ~ turn_22` 范围内的 entry

这一步几乎零成本，而且通常收益最高。

---

## 第二步：按类型筛

先粗判 query 属于哪种类型，再缩 entry 类型。

### follow-up 类 query

示例：

- “那这个上限呢”
- “另一个呢”
- “你刚才第二点呢”

优先保留：

- `resolved_query`
- `answer_unit`
- `focus_task`

### challenge 类 query

示例：

- “你刚才这个说法不对吧”
- “第二点有什么依据”
- “你漏了例外情形”

优先保留：

- `answer_unit`
- `user_assertion`
- `review_outcome`

### 普通知识问答类 query

示例：

- “一年期劳动合同试用期上限是多少”

优先保留：

- `resolved_query`
- `focus_task`

---

## 第三步：按显式模式筛

这一步是你最关心的“规则能不能命中”的核心。

规则只做少数高精度模式，不碰开放式语义判断。

### 多目标模式

命中词：

- `前两个`
- `这两个`
- `两个`
- `分别`
- `都`

行为：

- 候选按时间和置信度排序后，保留前 2 个或前 N 个

### 序号模式

命中词：

- `第一个`
- `第二个`
- `第三点`
- `上一条`

行为：

- 优先选 `answer_unit.structured_payload.unit_index`
- 或按最近排序后的第 N 个候选

### 指代模式

命中词：

- `这个`
- `那个`
- `这个说法`
- `那个结论`
- `你刚才说的`

行为：

- 优先只保留：
  - 最近的 `answer_unit`
  - 最近的 `user_assertion`
  - 最近的 `review_outcome`
- 如果只剩 1 条高置信候选，直接命中
- 如果还剩多条，不做硬判，进入小模型 resolution

### challenge 信号模式

命中词：

- `依据`
- `为什么`
- `不对`
- `有问题`
- `漏了`
- `不成立`

行为：

- 强制提升 `answer_unit` 与 `user_assertion` 权重
- 降低 `resolved_query` 权重

---

## 第四步：confidence / status 筛

规则：

- 只保留 `status=active`
- 默认保留 `confidence=high|medium`
- `low` 只在没有其他候选时才兜底保留

这一步的目标是：

- 不把低置信记忆送进最终 resolution

---

## 规则命中示例

### 示例 1

当前 query：

```text
你刚才第二点的依据呢
```

规则命中：

1. 时间窗口筛
  - 保留最近 6 条 entry
2. 类型筛
  - challenge 类，优先保留 `answer_unit`、`user_assertion`、`review_outcome`
3. 显式模式筛
  - 命中 `第二点`
  - 从 `answer_unit.unit_index=2` 的 entry 中优先保留
4. confidence/status 筛
  - 如果只剩 `wm_answer_002`
  - 直接命中，不调模型

### 示例 2

当前 query：

```text
那个说法不太对吧
```

规则命中：

1. 时间窗口筛
2. 类型筛
  - challenge 类
3. 显式模式筛
  - 命中 `那个说法`
  - 优先保留最近的 `answer_unit` 与 `user_assertion`
4. 结果剩 3 条
  - 不做硬判
  - 交给小模型做最终 resolution

### 示例 3

当前 query：

```text
前两个分别怎么处理
```

规则命中：

1. 时间窗口筛
2. 类型筛
  - follow-up / compare 候选
3. 显式模式筛
  - 命中 `前两个` + `分别`
  - 保留最近排序前 2 个候选
4. 如果两条都高置信
  - 可直接输出两个 target

---

## 什么时候调用小模型

只有在这些情况才调用：

1. 当前 query 有指代
2. 当前 query 有省略
3. 当前 query 是 challenge
4. 规则筛完后候选数量在 `2~5` 条
5. 规则无法高置信唯一命中

其他情况：

- 不调用模型

---

## 小模型输入与输出

### 输入

只给：

1. 当前 query
2. 最近 `2~4` 轮对话
3. 规则筛后的 `3~5` 条候选 entry

### 输出

```json
{
  "resolved_entry_ids": ["wm_answer_002"],
  "resolved_target_kind": "answer_unit",
  "rewritten_query": "一年期劳动合同试用期上限的依据是什么",
  "confidence": "high",
  "needs_clarification": false
}
```

这样做的目标是：

- 不让模型看全量记忆
- 不让模型做开放式长推理
- 只做一个窄任务

---

## Binding 与 Challenge 的共用对象池

建议 `binding` 和 `challenge` 共用同一个 target pool。

这个 pool 由：

- 最近几轮 transcript
- 小规模 `working_memory` entries
- registry 中的高可靠对象
- 必要时的 memory anchor

共同组成。

### `binding` 的消费方式

- 目标是得到：
  - `resolved_target_ids`
  - `rewritten_query`

### `challenge` 的消费方式

- 目标是得到：
  - 当前被质疑的是哪个 `answer_unit` / `user_assertion` / `question_object`

差别在消费方式，不在对象来源。

---

## Challenge 正式主链

```text
resolve challenge target
-> check existing evidence
-> if sufficient: answer
-> else retrieve more evidence
-> adjudicate
-> answer
```

解释：

1. 先 resolve 被质疑对象
2. 先看已有 evidence 是否足够
3. 够则直接回答
4. 不够再补检索
5. 再输出：
  - supported
  - partially_supported
  - insufficient_evidence
  - contradicted

这里的关键是：

- 不是“给证据找证据”
- 而是“给被质疑对象找证据”

---

## 第一版最小落地建议

如果现在就开始做，第一版建议只做这些：

### 存储

- `session_xxx.working_memory.jsonl`
- `session_xxx.working_memory.head.json`

### entry 类型

- `focus_task`
- `resolved_query`
- `answer_unit`
- `user_assertion`
- `review_outcome`

### 规则筛选

- 最近窗口筛
- 类型筛
- 显式模式筛
- confidence/status 筛

### 小模型使用条件

- 候选 > 1
- query 有指代/省略/challenge

### challenge

- 先 resolve target
- 先 check existing evidence
- 不够再 retrieve

---

## 当前建议与现状的关系

当前仓库现状还不是这套完整实现。

当前已有的是：

- `session_working_memory` 的轻量 metadata 版本
- `ContextBindingPower` 的本地 `state_snapshot`
- `ChallengePower` 的基础 challenge 主链

这份文档给的是：

- 下一版正式 working memory 设计
- 以及 `binding / challenge` 共用对象池的落地方向

