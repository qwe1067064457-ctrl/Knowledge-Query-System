# observability

## 职责

这个目录只负责：

- 事实采集
- 共享证据 schema
- 轻量 trace context
- LangSmith-first 投影

## 不负责

- 不负责运行态健康判断
- 不负责质量打分
- 不负责 dashboard / alert

这些分别留给后续：

- `backend/monitoring/`
- `backend/evaluation/`

## 当前阶段

当前只覆盖：

- `workflow_run`
- `answer_model_run`
- `retrieval_run`
- `context_assembly_run`
- `compaction_run`
- `pre_compaction_extraction_run`

并且只做轻量摘要，不落重型本地证据仓。
