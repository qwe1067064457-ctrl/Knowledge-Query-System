# Workflow Prompt Rules

这个目录存放从 workflow 投影到主回答 prompt 的规则说明。

文件说明：

- `answer_behavior_rules_from_workflow.md`
  - workflow 的 route、handling mode、policy flags 如何影响主回答行为。
- `answer_result_projection_rules_from_workflow.md`
  - workflow 已产出的执行结果如何投影成主回答 prompt 的可见信息。
- `bound_query_rewrite_prompt.md`
  - 用于 context binding 的 resolution / rewrite prompt。
  - 输入来源固定为：`binding_snapshot`、最近少量对话、候选相关对象、当前用户问题。
  - 输出 contract 固定为：
    - `resolved_target_ids`
    - `rewritten_query`
    - `confidence`
    - `needs_clarification`
    - `fallback_type`
    - `reason`
