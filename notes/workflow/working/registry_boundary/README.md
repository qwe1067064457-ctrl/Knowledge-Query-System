# Registry Boundary README

这个目录用于记录当前 goal：`workflow 与 context registry 的正式边界与消费口径`。

使用原则：

- 这里只记录本 goal 的活跃状态、阶段性判断和压缩交接。
- 已经稳定的长期结论继续复用 `docs/adr/`。
- 不回写上一个 goal 的：
  - `refinement/`
  - `p1_stabilization/`
  - `answer_alignment/`

文件职责：

- `todo.md`
  - 当前轮次、当前 focus、下一步、完成标准。
- `compression_handoff.md`
  - 压缩前后的快速续接摘要。
- `decisions.md`
  - 本 goal 内新确认的边界决策与理由。
- `known_issues.md`
  - 仍然接受的兼容层、暂不继续扩大的边界点。

本阶段重点：

- 澄清 `workflow -> registry` 的高频消费口径。
- 区分 registry metadata 里：
  - `workflow_summary`
    - 来自 workflow owner 的正式摘要输出。
  - `registry_convenience`
    - 为持久化、检索、回放提供的便利字段。
