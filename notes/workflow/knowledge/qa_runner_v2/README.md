# QA Runner V2 Knowledge

这个目录用于沉淀 `QA Runner V2` 的稳定工程知识。

这里不记录按时间推进的 working 过程，不承载压测轮次、临时 blocker、handoff 和 todo。这里重点保留：

- 当前有效的架构定位
- 稳定 contract
- 模块 owner 与边界
- runtime / harness 可观测模型
- 当前已定版的工程决策

如果你想看阶段性过程、压测记录、handoff 和当前待办，请转到：

- [working/qa_runner_v2/README.md](/C:/Users/HUAWEI/PycharmProjects/Skill-First-Hybrid-RAG/notes/workflow/working/qa_runner_v2/README.md)

推荐阅读顺序：

1. [architecture/route_layer.md](/C:/Users/HUAWEI/PycharmProjects/Skill-First-Hybrid-RAG/notes/workflow/knowledge/qa_runner_v2/architecture/route_layer.md)
2. [architecture/execution_flow.md](/C:/Users/HUAWEI/PycharmProjects/Skill-First-Hybrid-RAG/notes/workflow/knowledge/qa_runner_v2/architecture/execution_flow.md)
3. [contracts/execution_payload.md](/C:/Users/HUAWEI/PycharmProjects/Skill-First-Hybrid-RAG/notes/workflow/knowledge/qa_runner_v2/contracts/execution_payload.md)
4. [modules/challenge_and_review.md](/C:/Users/HUAWEI/PycharmProjects/Skill-First-Hybrid-RAG/notes/workflow/knowledge/qa_runner_v2/modules/challenge_and_review.md)
5. [modules/memory_anchor_and_hydration.md](/C:/Users/HUAWEI/PycharmProjects/Skill-First-Hybrid-RAG/notes/workflow/knowledge/qa_runner_v2/modules/memory_anchor_and_hydration.md)
6. [runtime/harness_event_model.md](/C:/Users/HUAWEI/PycharmProjects/Skill-First-Hybrid-RAG/notes/workflow/knowledge/qa_runner_v2/runtime/harness_event_model.md)
7. [decisions/follow_up_vs_handling_mode.md](/C:/Users/HUAWEI/PycharmProjects/Skill-First-Hybrid-RAG/notes/workflow/knowledge/qa_runner_v2/decisions/follow_up_vs_handling_mode.md)
8. [decisions/known_seams.md](/C:/Users/HUAWEI/PycharmProjects/Skill-First-Hybrid-RAG/notes/workflow/knowledge/qa_runner_v2/decisions/known_seams.md)

当前知识层默认基线：

- `chat` 是轻对话响应流
- `qa` 是受控单轮答复执行流
- `orchestrated` 是多步执行编排流
- `challenge` 属于 `qa route` 内部分支
- `follow_up` 不进入 `handling_mode`
- 对外 `route / handling_mode` 继续保持 string contract
