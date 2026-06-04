# Compaction Rubric

## 维度

- `key_info_preserved`
  - 压缩后关键信息是否仍被保留
- `anchor_recoverability`
  - 历史锚点是否仍可回溯
- `post_compaction_sufficiency`
  - 压缩后上下文是否仍足够支撑判断
- `pre_compaction_extraction_coverage`
  - pre-compaction extraction 是否覆盖应保留内容

## 原因标签

- `lost_key_info`
  - 关键信息在 compaction 后丢失
- `lost_anchor`
  - 历史锚点在 compaction 后无法恢复
- `insufficient_post_context`
  - 压缩后的上下文不足以继续判断
- `extraction_missed`
  - pre-compaction extraction 没覆盖应保留内容
