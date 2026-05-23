# Answer Behavior Rules From Workflow

这些规则描述 workflow 的运行模式如何影响主回答模型的行为：

- `should_ask_clarification_first`
  - 主回答模型必须先澄清，不进入完整答案。
- `handling_mode=challenge`
  - 主回答模型必须重新审视争议点，不能机械维护旧答案。
- `handling_mode=scope_info`
  - 主回答模型回答系统能力或范围，不执行底层任务。
- `handling_mode=unsupported`
  - 主回答模型简短拒绝，并尽可能提供安全替代方向。
- `route=orchestrated`
  - 主回答模型应显式体现阶段顺序。
- `route=qa`
  - 主回答模型保持轻量回答，不额外展开结构化过程。
- `route=chat`
  - 主回答模型自然回复，不做过度结构化。
- `use_planner / decompose_query / cite_sources / use_context`
  - 这些 flag 会进一步补充主回答行为约束。
