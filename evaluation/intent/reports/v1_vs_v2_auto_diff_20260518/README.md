# V1 vs V2 Auto Diff 20260518

这个目录保存 `V1 legacy` 标签与 `V2 auto` 自动重标之间的结构化差异报告。

## 文件组成

- `summary.json`
  - 总体统计
- `report.md`
  - 人类可读摘要

## 当前用途

- 快速看 `V2` 相对 `V1` 改了哪些字段
- 判断变化主要集中在哪些维度：
  - `main_intent`
  - `task.shape`
  - `task.topology`
  - `context_dependency`
  - `control.route/mode`
- 给 `V2 reviewed` 的人工复核范围排序

## 使用建议

- 不把这个目录当训练数据
- 把它当迁移风险定位与质量分析输入
