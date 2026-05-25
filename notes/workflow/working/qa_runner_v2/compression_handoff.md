# QA Runner V2 Compression Handoff

当前主线已经确认：

- 代码边界使用 `route / power / worker / helper`
- `capabilities/` 不再视为长期 owner
- QA 正式主链：
  - `need_retrieval gate -> retrieval -> retrieval_quality -> challenge/review -> payload -> answer`
- `session working memory`
  - 只保执行连续性
  - 不参与 bound query 主判断
- memory 命中不应只返回摘要
  - 要支持 `anchor -> hydrate`

继续工作前优先看：

1. `architecture.md`
2. `contracts.md`
3. `retrieval_and_challenge.md`
4. `memory_anchor_and_hydration.md`
5. `todo.md`
