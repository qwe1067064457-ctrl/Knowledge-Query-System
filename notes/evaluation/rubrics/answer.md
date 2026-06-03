# Answer 评判标准

## 评什么

- 评最终回答质量
- 可参考 `Knowledge evidence + core + workflow/context 摘要`
- 不评文风，不把主观喜欢当真值

## 维度

- `answered`
- `grounded`
- `consistency_with_evidence`
- `constraint_coverage`
- `no_hallucination`

## 综合分

```text
answer_score =
0.25 * answered
+ 0.30 * grounded
+ 0.20 * consistency_with_evidence
+ 0.15 * constraint_coverage
+ 0.10 * no_hallucination
```

## 硬门槛

- `answered = bad` -> 整体直接 `bad`
- `consistency_with_evidence = bad` -> 整体最高 `weak`
- `no_hallucination = bad` -> 整体最高 `weak`
