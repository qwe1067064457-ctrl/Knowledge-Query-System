# QA Runner E2E 样本集

## 说明

这批样本用于 `QA Runner` 端到端验证。

每条样本不是只有 query，而是：

- query
- recent_messages
- working_memory
- registry_entries
- memory_anchors（如需要）

同时观察两层结果：

1. `QA Runner payload`
2. 主回答模型输出

## 当前样本策略

- 主样本只取当前线程近 20 轮真实对话
- 当前先把真实主样本提升到 8 条
- 不额外扩大人工样本面

## 当前 8 条真实主样本

### E2E-R1

- query: `是不是使用context binding power才能得到relevant set?`
- 类型: self-contained architecture question
- 预期:
  - `QA Runner` 不应出现噪音扩散
  - `binding` 即使不深度介入，也应给出稳定 payload
  - 主回答模型应能给出清晰解释

### E2E-R2

- query: `ContextBindingPower应该来自于working_memory / recent candidates / memory_anchors? working_memory 来自于原始近对话?`
- 类型: self-contained compare question
- 预期:
  - 不应误绑成 `multi_target`
  - 主回答模型应能解释 source layering

### E2E-R3

- query: `这不是意图识别的问题吗?`
- 类型: weak explicit follow-up
- 预期:
  - `binding` 可以较粗，但 relevant set 不应塌
  - 主回答模型应能沿着上一轮解释继续回答

### E2E-R4

- query: `所以,不管是哪种场景,我们都需要有一个relevant set,后面是不是要真正的消费这个relevant的set?`
- 类型: summary follow-up
- 预期:
  - 允许保守
  - 若进入 clarification，不应带偏主回答

### E2E-R5

- query: `所以現在模型的调通了,只是返回結果不穩定。`
- 类型: confirmation follow-up
- 预期:
  - `binding` 应能继续锚定“live llm path”
  - 主回答模型应明确区分“路径打通”和“结果稳定”

### E2E-R6

- query: `那是模型的问题, 不是我们prompt问题?`
- 类型: challenge-like architecture follow-up
- 预期:
  - `binding` 应尽量恢复到“归因边界”这一 topic
  - 主回答模型应保守回答，不该直接单点归因

### E2E-R7

- query: `调用模型能力用的langchain还是openai sdk`
- 类型: self-contained architecture question
- 预期:
  - `QA Runner` 可直接给稳定 payload
  - 主回答模型应清楚回答“代码层 vs 底层 SDK”

### E2E-R8

- query: `那我们现在怎么做? 就是还要去调大模型吗?现在build model里面我们调的是MiniMax了。`
- 类型: recommendation follow-up
- 预期:
  - `binding` 应尽量恢复到“下一步策略”
  - 主回答模型应给出可执行建议，而不是只复述现状

## 当前 challenge coverage 真实样式补样本

### E2E-C1

- query: `那是模型的问题, 不是我们prompt问题?`
- 类型: challenge-like architecture follow-up
- 输入重点:
  - target 有稳定 `question_object`
  - existing evidence 只有 related-only 文本相关，没有 grounded ref
- 预期:
  - `ReviewWorker` 不应把 related-only evidence 直接算 sufficient
  - `retrieve_if_needed.reason = related_evidence_not_grounded`
  - follow-up retrieval 应只围绕 disputed target 发生

### E2E-C2

- query: `那是模型的问题, 不是我们prompt问题?`
- 类型: challenge-like architecture follow-up
- 输入重点:
  - 与 `E2E-C1` 相同 target
  - 不提供 retrieval recovery
- 预期:
  - 保持 `insufficient_evidence`
  - 不因 related-only existing evidence 误判 success
