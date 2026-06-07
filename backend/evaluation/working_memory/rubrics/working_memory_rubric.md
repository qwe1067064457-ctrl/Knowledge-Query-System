# Working Memory Rubric

## 维度

- `continuity_support`
  - 当前 working memory 是否足够支撑下一步执行连续性
- `key_state_capture`
  - 关键状态如 `focus_task / resolved_query / review_outcome` 是否被保留
- `noise_control`
  - 是否引入过多与当前任务无关的噪声条目
- `freshness`
  - 是否存在过多过期或 stale 条目
- `handoff_utility`
  - 另一轮执行者是否能基于当前 working memory 快速接手

## 原因标签

- `missing_focus_task`
  - 缺少关键 focus task
- `missing_resolved_query`
  - 缺少关键 resolved query
- `missing_review_outcome`
  - 缺少关键 review outcome
- `too_noisy`
  - 无关噪声条目过多
- `too_stale`
  - stale 条目过多
- `handoff_not_ready`
  - 当前 working memory 不足以支撑交接
