# Retrieval 评判标准

## 评什么

- 只评 `Knowledge retrieval` 质量
- 不评长期记忆检索
- 不评时延、吞吐、告警

## 维度

- `presence`
- `relevance`
- `sufficiency`
- `usability`

## 综合分

```text
retrieval_score =
0.20 * presence
+ 0.35 * relevance
+ 0.25 * sufficiency
+ 0.20 * usability
```

## 硬门槛

- `presence = bad` -> 整体直接 `bad`
- `relevance = bad` -> 整体最高 `weak`
