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
- `global_binding_frame_prompt.md`
  - 用于 `orchestrated` 的 global binding frame。
  - 只负责 frame / hint，不做 deep binding。
  - 允许输出：
    - `query_is_context_dependent`
    - `binding_scope_hint`
    - `shared_target_candidates`
    - `recommended_binding_mode`
    - `segment_hints`
    - `notes`
- `execution_graph_planner_prompt.md`
  - 用于 `orchestrated` 的模型化 planner。
  - 目标是生成最小可执行 `ExecutionGraph`。
  - 关键约束：
    - graph 必须是 DAG
    - 不要把 unit 拆得过碎
    - staged / conditional 优先表达依赖
    - 多个 branch 共用 retrieval / binding / answer slot 时优先合并
