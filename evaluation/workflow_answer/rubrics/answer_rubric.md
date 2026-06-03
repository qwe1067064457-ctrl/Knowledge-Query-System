# Answer Rubric

## 范围

这里只评最终回答质量，不评文风，不把用户主观 like/dislike 直接当真值。

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
- `ungrounded`
- `conflict_with_evidence`
- `missed_constraint`
- `hallucination`
