# QA Runner V2 README

这个目录承接 `QA Runner V2` 的独立工作线。

它与 `refinement/` 的关系是：

- `refinement/`
  - 视为 workflow v1 完善期主目录
- `qa_runner_v2/`
  - 视为 QA Runner V2 的独立专题目录

这里重点记录：

- QA 主链如何收口
- `route / power / worker / helper` 边界
- `retrieval gate / retrieval_quality / evidence_check` 的正式分层
- `session working memory` 的定位
- `daily_log / cases -> memory anchor -> context hydration` 的链路

推荐阅读顺序：

1. `architecture.md`
2. `contracts.md`
3. `working_memory_design.md`
4. `context_binding/README.md`
5. `retrieval_and_challenge.md`
6. `memory_anchor_and_hydration.md`
7. `todo.md`
8. `compression_handoff.md`
