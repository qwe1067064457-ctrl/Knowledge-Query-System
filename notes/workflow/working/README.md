# Workflow Working README

这个目录用于存放 `workflow` 主题下的中间态材料。

当前默认子目录：

- `refinement/`
  - workflow 完善阶段的主目录
- `qa_runner_v2/`
  - QA Runner V2 的独立专题目录
- `p1_stabilization/`
  - workflow 收口后的 P1 优化与稳定化目录
- `answer_alignment/`
  - workflow 与 answer side 的消费链对齐目录
- `registry_boundary/`
  - workflow 与 context registry 正式边界梳理目录

放置原则：

- 仍在快速变化的 workflow 结论，先放这里
- QA Runner V2 的检索链、challenge 分层、memory 回锚资料，优先放 `qa_runner_v2/`
- 一轮轮收口后的结构化状态，也放这里
- 只有明显稳定、已经适合长期引用的内容，才提炼到 `docs/` 或更稳定的主题层
- 不同 goal 如果要求外部记忆隔离，应使用不同子目录承接各自的活跃状态
