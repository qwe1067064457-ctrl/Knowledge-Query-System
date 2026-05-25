# Workflow Prompt Rules

这个目录存放从 workflow 投影到主回答 prompt 的规则说明。

文件说明：

- `answer_behavior_rules_from_workflow.md`
  - workflow 的 route、handling mode、policy flags 如何影响主回答行为。
- `answer_result_projection_rules_from_workflow.md`
  - workflow 已产出的执行结果如何投影成主回答 prompt 的可见信息。
- `state_update_prompt.md`
  - 用于短程对话运行态 `state` 更新的轻量 prompt。
  - 输入来源固定为：上一轮 `state`、最近少量对话、候选 `question_object`、候选 evidence topics、当前用户问题。
  - 输出 contract 固定为：
    - `focus_question_object_id`
    - `focus_question_object_text`
    - `focus_predicate`
    - `recent_question_objects`
    - `recent_evidence_topics`
    - `resolution_confidence`
    - `last_update_reason`
- `bound_query_rewrite_prompt.md`
  - 用于 bound query resolution / rewrite 的轻量 prompt。
  - 输入来源固定为：当前 `state`、最近少量对话、候选 `question_object`、当前用户问题。
  - 输出 contract 固定为：
    - `resolved_target_ids`
    - `rewritten_query`
    - `confidence`
    - `needs_clarification`
