# 易混淆信号对照

## 1. 文档目标

这份文档记录 `evidence` 层里容易混淆的信号。

最重要的原则：

```text
有些信号不能只看当前 query 文本判断。
history 经常会改变正确解释。
```

## 2. `qa` vs `chat`

### `qa`

用户在问知识、判断、解释或处理建议。

例子：

```text
合同无效的情形有哪些？
这样算医疗事故吗？
事情越来越复杂了，我该怎么处理？
```

### `chat`

用户在寒暄、感谢或表达非任务消息。

例子：

```text
你好
谢谢，明白了
最近感觉事情越来越复杂。
```

### 边界

```text
最近感觉事情越来越复杂。
```

更像 `chat`。

```text
事情越来越复杂了，我该怎么处理？
```

更像 `qa`。

## 3. `qa` vs `ask_source`

### `qa`

用户问对象本身。

例子：

```text
医疗事故怎么认定？
```

### `ask_source`

用户问某个回答或判断的依据。

例子：

```text
依据是什么？
有法条依据吗？
你刚才为什么这么说？
```

### 边界

```text
医疗事故怎么认定？
```

这是问知识本身。

```text
你刚才说医疗事故要举证，这个依据是什么？
```

这是问上一轮说法的依据。

## 4. `ask_source` vs `soft_doubt`

这两个在自然语言里经常重叠。

### `ask_source`

主轴是：

```text
请给我理由或来源。
```

例子：

```text
你刚才为什么这么说？
```

### `soft_doubt`

主轴是：

```text
我不完全相信/我在保留质疑。
```

例子：

```text
你确定吗？
```

### 重要边界

```text
你刚才为什么这么说？
```

这句话可以带质疑味道，但最稳定的语义轴是 `ask_source`。

如果把所有问依据的问题都判成 `soft_doubt`，会把很多正常引用/来源请求误判成 challenge。

更强的表达：

```text
你刚才为什么这么说？我感觉这个结论不太对。
```

这时可以同时有：

- `ask_source`
- `soft_doubt`，甚至 `challenge`

## 5. `challenge` vs `soft_doubt`

### `challenge`

用户明确反驳或指出回答错误。

例子：

```text
你说错了。
这个结论不对。
你搞错了。
```

### `soft_doubt`

用户表达轻质疑或求证式怀疑。

例子：

```text
你确定吗？
真的吗？
这个说法是不是太绝对了？
```

### 边界

```text
你是不是搞错了？
```

这比普通 `soft_doubt` 更强，可能更接近硬 `challenge`。

```text
这个说法是不是太绝对了？
```

如果有上一轮回答，通常是 `soft_doubt`。

如果没有上一轮回答，可能是 ambiguous，也可能根据完整 query 变成普通 QA。

## 6. `soft_doubt` vs 普通 `qa`

这是最重要的边界之一。

### 带不确定语气的普通 QA

```text
这种规则是不是全国都适用？
```

没有相关 history 时，它常常是普通 `qa`，也可能是 `needs_clarification`。

不应只因为有“是不是”就自动判成 `soft_doubt`。

### 有 history 的 soft doubt

History:

```text
assistant: 这种规则全国都适用。
```

User:

```text
这种规则是不是全国都适用？
```

这时它可以是：

- `follow_up`
- `soft_doubt`

质疑对象是上一轮 claim。

### 判断原则

```text
"是不是" 不够。
关键看用户是在问新知识，还是在怀疑上一轮 claim。
```

## 7. `follow_up` vs `needs_clarification`

### `follow_up`

query 能接上历史上下文。

有 history 的例子：

```text
user: 医疗事故怎么认定？
assistant: ...
user: 那这种情况呢？
```

这是 `follow_up`。

### `needs_clarification`

query 依赖缺失上下文，或缺少足够事实。

没有 history 的例子：

```text
那这种情况呢？
```

这不是稳定 follow-up，因为系统不知道“这种情况”指什么。

应该转成 `needs_clarification`。

## 8. `ask_source` vs `challenge`

### `ask_source`

用户问依据。

例子：

```text
你这个说法依据是什么？
```

### `challenge`

用户否定回答。

例子：

```text
你这个说法不对。
```

### 混合例子

```text
你这个说法依据是什么？我觉得明显不对。
```

这可以合理地产生多值 evidence：

- `ask_source`
- `challenge`

evidence 层允许多值和冲突。

## 9. `complex` vs `TaskCandidate.shape`

### `complex`

这是粗任务信号。

它表示：

```text
query 可能不适合简单 QA，需要更复杂执行。
```

### `TaskCandidate.shape`

这是更细的任务形态：

- `compare`
- `summarize`
- `extract`
- `verify`
- `mixed`

### 边界

`complex` 是业务信号。

`compare`、`summarize`、`verify`、`mixed` 当前不是 raw bucket signal。

它们是 task candidate 推导结果。

## 10. `needs_clarification` vs `qa`

这两个概念可以共存。

例子：

```text
这样算医疗事故吗？
```

它可能是：

- `qa`，因为它在问判断型问题
- `needs_clarification`，如果缺少足够事实

所以不要把 `needs_clarification` 理解为“不是 QA”。

它表示：

```text
大概率是 QA，但信息不足，不能安全直接答。
```

