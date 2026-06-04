# monitoring

这里承接运行态健康系统的一期最小实现。

当前共识：

- `monitoring` 消费 `backend/observability/` 的共享证据
- 主链口径采用分层视图：
  - `request -> intent -> context -> workflow -> action -> answer`
- `retrieval / compaction / pre_compaction_extraction` 是可选分支，不是固定主干
- 后续 `intent` 监测会继续接入同一 `trace`，不需要重做这层结构
