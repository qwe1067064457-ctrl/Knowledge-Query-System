# 业务信号目录

## 1. 什么是业务信号

业务信号是 `signal_buckets` 里的粗粒度信号。

它不是最底层的规则命中。

它也不是最终 resolved 决策。

它的位置是：

```text
matched_rules -> signal_buckets -> candidate_intents / task_candidates -> resolved
```

## 2. 当前 bucket

`signal_buckets` 当前分为四组：

- `intent`
- `task`
- `context`
- `safety`

## 3. Intent Bucket

`intent` bucket 回答：

```text
当前 query 显露出什么意图或意图类语义力量？
```

当前信号：

- `qa`
- `chat`
- `system`
- `ask_capability`
- `ask_source`
- `challenge`
- `soft_doubt`

### `qa`

含义：

用户在问知识、解释、判断、对比、提取、验证或分析。

典型规则来源：

- `intent.qa.domain`
- `intent.qa.generic`
- `intent.qa.judgment`
- `intent.qa.long_context_rescue`
- `intent.qa.long_form`

例子：

```text
合同无效的情形有哪些？
这样算医疗事故吗？
如果公司拖欠工资，我可以怎么处理？
```

注意：

- `qa` 是主意图候选信号。
- `generic_qa` 和 `judgment_qa` 不是 bucket 里的 signal 名，它们是会映射到 `qa` 的规则类型。

### `chat`

含义：

用户在寒暄、感谢、确认、表达轻量闲聊或情绪。

典型规则来源：

- `intent.chat.greeting`

例子：

```text
你好
谢谢，明白了
最近感觉事情越来越复杂。
```

边界：

```text
最近感觉事情越来越复杂。
```

更像 `chat`。

```text
事情越来越复杂了，我该怎么处理？
```

更像 `qa`。

### `system`

含义：

用户在问系统能力、支持范围、使用方式或系统身份。

典型规则来源：

- `system.capability.ask`

例子：

```text
你能做什么？
你支持哪些功能？
你可以帮我分析知识库吗？
```

### `ask_capability`

含义：

更具体的能力咨询信号。

它通常支持 `system` 作为主意图候选。

例子：

```text
你能做什么？
这个系统支持什么？
```

注意：

- 当前它放在 `intent` bucket。
- 它更像 `system` 的 modifier-like 信号。

### `ask_source`

含义：

用户在问依据、来源、引用、证据，或为什么前面那样说。

典型规则来源：

- `source.ask_basis`

例子：

```text
依据是什么？
你刚才为什么这么说？
有法条依据吗？
```

注意：

- `ask_source` 可以同时出现在 `intent` bucket 和 `context` bucket。
- 在 `intent` bucket 中，它表示“问依据/来源”。
- 在 `context` bucket 中，它表示“这个来源追问可能依赖上一轮回答”。

### `challenge`

含义：

用户明确反驳、否定，或指出回答有问题。

典型规则来源：

- `challenge.disagree`

例子：

```text
你说错了。
这个结论不对。
你搞错了。
```

注意：

- 这是硬质疑。
- 它比 `soft_doubt` 更强。

### `soft_doubt`

含义：

用户表达轻质疑、保留态度、求证式怀疑。

典型规则来源：

- `challenge.soft_doubt`

例子：

```text
你确定吗？
这个说法是不是太绝对了？
真的吗？
```

重要边界：

```text
这种规则是不是全国都适用？
```

这句话可能是普通 `qa`，也可能是 `follow_up` 或 `soft_doubt`，关键看上文。

如果没有相关上一轮回答，不应仅凭“是不是”自动判成 `soft_doubt`。

如果上一轮明确说“这种规则全国都适用”，那同一句话可能就是 `soft_doubt` 或 `follow_up`。

## 4. Task Bucket

`task` bucket 回答：

```text
当前 query 显露出什么任务形态或复杂度信号？
```

当前信号：

- `multi_question`
- `complex`

### `multi_question`

含义：

query 包含多个问题，或有明显并列/枚举结构，可能需要拆解。

典型规则来源：

- `task.enumerated_questions`

例子：

```text
合同无效有哪些情形？如果已经履行了怎么办？
第一，如何认定？第二，怎么举证？
```

注意：

- 它通常会推向 `TaskCandidate(compound, multi_question, 0.9)`。
- 它不单独决定主意图，多问任务仍然可能是 `qa`。

### `complex`

含义：

query 需要超过简单问答的处理方式，可能涉及对比、验证、总结、提取或结构化分析。

典型规则来源：

- `task.complex.request`

例子：

```text
请对比这两种制度的差异。
请逐条核对这些判断是否成立。
请总结争议点、关键事实和判断依据。
```

注意：

- `complex` 不等于 `compare`、`summarize`、`extract`、`verify`、`mixed`。
- 后面这些是 `TaskCandidate.shape` 推导出来的更细任务形态。

## 5. Context Bucket

`context` bucket 回答：

```text
当前 query 显露出什么上下文语义信号？
```

当前信号：

- `ask_source`
- `challenge`
- `soft_doubt`
- `follow_up`
- `needs_clarification`

### 为什么有些信号也出现在 intent

有些信号是双轴语义：

- `ask_source`
- `challenge`
- `soft_doubt`

它们同时描述：

- 用户的意图类力量
- query 和上文的关系

例子：

```text
你刚才为什么这么说？
```

它既是：

- `intent` 轴上的 `ask_source`
- 如果有上一轮回答，也是 `context` 轴上的上下文追问

### `follow_up`

含义：

用户在接着上文继续问。

典型规则来源：

- `context.follow_up.reference`

例子：

```text
那这种情况呢？
如果是公司呢？
刚才那种情形怎么算？
```

边界：

- 有可用 history：更像 `follow_up`。
- 没有可用 history：经常转成 `needs_clarification`。

### `needs_clarification`

含义：

系统应该先向用户澄清，再继续回答。

典型规则来源：

- `context.follow_up.missing_history`
- `challenge.missing_context`
- `source.missing_context`
- `intent.qa.judgment_clarify`

例子：

```text
那这个呢？
这样算违法吗？
你刚才为什么这么说？  # 如果没有上一轮回答
```

注意：

- `needs_clarification` 不等于“不是 QA”。
- 它表示“可能是 QA，但当前还不适合直接答”。

## 6. Safety Bucket

`safety` bucket 回答：

```text
这个请求是否应该离开普通 QA 流程？
```

当前信号：

- `unsupported`
- `out_of_scope`

### `unsupported`

含义：

用户要求执行当前入口不支持的操作。

典型规则来源：

- `unsupported.file_delete_request`
- `unsupported.file_write_request`
- `unsupported.kb_admin_request`
- `unsupported.privileged_operation`
- `unsupported.unknown_external_action`

例子：

```text
帮我删除知识库里的文件。
替我上传这份资料到知识库。
调用外部系统处理一下。
```

### `out_of_scope`

含义：

一个更抽象的安全/业务标签，表示请求不应继续走普通 QA。

注意：

- `unsupported` 和 `out_of_scope` 通常一起出现。
- `unsupported` 更像不支持判断。
- `out_of_scope` 更像解释性标签。

