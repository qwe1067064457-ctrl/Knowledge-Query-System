# Answer Result Projection Rules From Workflow

这些规则描述 workflow 已经执行出的结果如何进入主回答 prompt：

- `context_summary`
  - 投影 binding summary，帮助主回答模型锚定当前目标上下文。
- `plan_summary`
  - 投影 planning mode、step count、checkpoint count 等，用于约束回答组织方式。
- `review_summary`
  - 投影 review mode、scope、confidence、status 及后续检索状态，用于显式表达不确定性。
- `evidence_summary`
  - 投影 retrieval quality、evidence count、source count、missing evidence 等，用于约束证据表达强度。
- `answer_constraints`
  - 投影为主回答模型的附加约束提示，不直接替代 evidence 或 review 本体。
