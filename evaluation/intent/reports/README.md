# Reports

`reports/` 存放 intent 评估活动的结果报告。

## 文件类型

- `*_report.md`
  - 面向阅读的结论说明
- `*_summary.json`
  - 面向脚本或后续处理的结构化结果

## 当前内容理解

- `query_list_campaign_v1_*`
  - 一轮 query list 评估活动
- `user_batch_v1_*`
  - 一轮用户批次评估活动
- `v1_adversarial_campaign_*`
  - 对抗样本活动
- `twins_campaign_v2_*`
  - twins 对比活动
- `intent_query_full_set_campaign_v1_summary*.json`
  - 同一评估活动在多轮修正后的 summary 快照

## 维护建议

- 同一轮活动同时保留 `report.md` 和 `summary.json` 很合理
- 如果是同一活动的多轮修正，命名里继续保留 `after_*` 后缀，便于追踪改进过程
- 当某一轮活动已经成为稳定结论，可以后续再单独抽总结，不需要现在删除历史快照
