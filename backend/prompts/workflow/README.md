# Workflow Prompt Rules

这个目录只存放从 workflow 投影到主回答 prompt 的规则说明。

文件说明：

- `answer_behavior_rules_from_workflow.md`
  - workflow 的 route、handling mode、policy flags 如何影响主回答行为。
- `answer_result_projection_rules_from_workflow.md`
  - workflow 已产出的执行结果如何投影成主回答 prompt 的可见信息。

非主回答 prompt 不再放在这里：

- context binding rewrite prompt
  - 放在 `backend/workflow/powers/prompts/`
- global binding frame prompt
  - 放在 `backend/workflow/orchestrated/binding/prompts/`
- execution graph planner prompt
  - 放在 `backend/workflow/orchestrated/planning/prompts/`
