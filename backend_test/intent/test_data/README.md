# Intent 测试数据

这个目录用于存放 `intent` 模块的评估测试数据。

当前按批次分类：

- `simple_qa.json`
- `chat.json`
- `follow_up.json`
- `challenge.json`
- `ask_source.json`
- `system.json`
- `unsupported.json`
- `compound_multi_question.json`
- `complex_task.json`
- `ambiguous.json`

每个文件都是一个 JSON 数组，元素结构与 `evaluation/intent/dataset_schema.md` 保持一致。

当前额外补充了：

- `gold.evidence.rule_expectations`

这个字段用于严格规则评估，支持后续统计：

- `tp`
- `fp`
- `fn`
- `tn`
- `precision`
- `recall`

建议用法：

```bat
py evaluation\intent\evaluate_intent_rules.py --dataset backend_test\intent\test_data
py evaluation\intent\evaluate_intent_rules.py --dataset backend_test\intent\test_data --markdown-out backend_test\intent\test_data\intent_eval_report.md
```
