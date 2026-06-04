# Answer Rubric

## 范围

这里只评最终回答质量，不评文风，不把用户主观 like/dislike 直接当真值。

## 术语

- `grounded`
  - 含义：回答建立在当前可见证据与上下文上，而不是脱离依据自行发挥。
- `constraint`
  - 含义：用户问题中明确提出的条件、限制、要求或边界。
- `hallucination`
  - 含义：回答出现证据没有支持、且看起来像模型自行编造的内容。
- `adjudication`
  - 含义：在最终结果出来之后，判断该样本是否需要人工复核的过程。
- `fallback`
  - 含义：模型层失败时，最终整理层回退到规则层结果。
- `aggregation`
  - 含义：把规则层与模型层结果合成最终维度标签、总分和复核标记的过程。

## 维度

- `answered`
  - `good`：正面回答了用户问题
  - `weak`：部分回答
  - `bad`：基本没回答
- `grounded`
  - `good`：明显立在证据与上下文上
  - `weak`：看起来有依据，但不够稳
  - `bad`：基本脱离证据
- `consistency_with_evidence`
  - `good`：与证据一致
  - `weak`：没有明显冲突，但存在模糊地带
  - `bad`：与证据冲突
- `constraint_coverage`
  - `good`：关键要求和约束都覆盖
  - `weak`：有遗漏但不致命
  - `bad`：遗漏关键要求
- `no_hallucination`
  - `good`：没有明显编造
  - `weak`：存在轻微不稳
  - `bad`：明显编造

## 权重

- `answered = 0.25`
- `grounded = 0.30`
- `consistency_with_evidence = 0.20`
- `constraint_coverage = 0.15`
- `no_hallucination = 0.10`

## 原因标签

- `missed_question`
  - 含义：回答没有正面回应用户当前问题，或者大部分内容在回避、跑题。
  - 触发：`answered = bad`。
  - 边界：回答不完整但仍然在正面回应问题时，不应直接标成 `missed_question`。
- `ungrounded`
  - 含义：回答没有明显建立在现有证据和上下文上，更像模型自行发挥。
  - 触发：`grounded = bad`。
  - 边界：证据较少但回答仍尽量贴近现有信息时，不应轻易标成 `ungrounded`。
- `conflict_with_evidence`
  - 含义：回答内容与当前可见证据冲突，二者不能同时成立。
  - 触发：`consistency_with_evidence = bad`。
  - 边界：证据不足导致无法核实，不等于一定冲突。
- `missed_constraint`
  - 含义：用户明确提出的关键条件、限制或要求没有被覆盖。
  - 触发：`constraint_coverage = bad`。
  - 边界：轻微遗漏但不影响主结论时，不应轻易标成 `missed_constraint`。
- `hallucination`
  - 含义：回答出现证据里没有支持、且看起来像编造出来的信息。
  - 触发：`no_hallucination = bad`。
  - 边界：只是表达模糊或保守推断，不应直接算 `hallucination`。
