# Workflow Answer Alignment TODO

current_round: 2  
last_completed_round: 2  
current_focus: graph answer side 的 registry/metadata 构建也已切到 typed bundle 入口，继续做完成度审计  
next_focus: 判断 backend/graph/agent.py 剩余 workflow 读法是否主要属于可接受兼容层，还是还有必须继续收的高频消费点

## In Progress

- [ ] 建立当前 goal 的独立阶段目录
  - 目标：让当前 goal 的活跃状态与 `refinement/`、`p1_stabilization/` 隔离
  - 完成标准：`README / todo / compression_handoff / decisions / known_issues` 已建立

- [ ] 收 answer side 的第一批高频 workflow summary 消费点
  - 目标：让 `backend/graph` 高概率优先走 `summary_view()` / accessor，而不是手工翻 summary dict
  - 完成标准：至少完成 1 处真实消费点收口，并有最小必要验证

## Next

- [ ] 继续扫描 `backend/graph/agent.py`
  - 目标：找还残留的 workflow summary dict 手工拼装或直读
- [ ] 判断剩余点是高频消费口，还是可接受兼容层

## Done Recently

- [x] `backend/graph/agent.py::_build_registry_entries_from_execution_payload(...)`
  现在优先消费：
  - `payload.context_bundle_obj()`
  - `payload.plan_bundle_obj()`
  - `payload.review_bundle_obj()`
  - `ContextBundle.bound_targets()`
  - `PlanBundle.query_unit_dicts()`
  而不是继续依赖 `payload.*_bundle.get(...)`
- [x] 新增黑盒测试：registry entry 构建可以直接从 typed bundle object 工作
- [x] workflow 黑盒回归提升到 `64 passed`
- [x] 新建 `notes/workflow/working/answer_alignment/`
  - `README.md`
  - `todo.md`
  - `compression_handoff.md`
  - `decisions.md`
  - `known_issues.md`
- [x] 当前 goal 的活跃状态已与 `refinement/`、`p1_stabilization/` 隔离
- [x] `notes/workflow/working/README.md` 已补 `answer_alignment/` 目录职责
- [x] `backend/graph/agent.py::_build_execution_summary_metadata(...)`
  现在优先消费：
  - `payload.context_summary_view()`
  - `payload.plan_summary_view()`
  - `payload.review_summary_view()`
  - `payload.evidence_summary_view()`
  - 以及 `ReviewBundle` / `PlanBundle` 的高频 accessor
- [x] 新增黑盒测试：graph 侧 metadata 组装会优先反映 typed summary/accessor，而不是 stale summary dict
- [x] workflow 黑盒回归提升到 `63 passed`
- [x] 上一个 goal 已完成 workflow P1 稳定化
- [x] `docs/adr/` 继续作为稳定 workflow 结论的共用正式层

## Rules

- 当前 goal 的活跃状态不回写到 `refinement/` 或 `p1_stabilization/`
- answer side 优先消费：
  - `ContextBundle.summary_view()`
  - `PlanBundle.summary_view()`
  - `ReviewBundle.summary_view()`
  - `EvidenceBundle.summary_view()`
  - 以及高频 accessor
