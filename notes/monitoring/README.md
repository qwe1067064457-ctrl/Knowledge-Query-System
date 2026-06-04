# Monitoring README

`monitoring/` 用于承接项目的运行态监测系统设计与阶段性收口材料。

当前目录关注的是：

- 运行健康
- 性能与稳定性
- 异常与退化观察
- 基于 `backend/observability/` 的健康判断与聚合视图

当前明确不直接负责：

- 回答质量判断
- retrieval 准确率判断
- compaction 保真评分
- 人工标注与 grader 流程

这些属于 `evaluation/`。

## 当前入口

- 交接文档：
  - [handoff/README.md](C:/Users/HUAWEI/PycharmProjects/Skill-First-Hybrid-RAG/notes/monitoring/handoff/README.md)
- 一期规划：
  - [phase1_plan.md](C:/Users/HUAWEI/PycharmProjects/Skill-First-Hybrid-RAG/notes/monitoring/phase1_plan.md)

## 当前共识

- `observability` 负责事实采集，不做高层健康判断
- `monitoring` 消费共享证据，做运行态健康、性能、稳定性观察
- `monitoring` 与 `evaluation` 不混做
- 第一阶段先围绕 `Workflow + 主回答模型 + retrieval/context/compaction`
- 暂不扩到 intent 层

## 建议阅读顺序

1. 先读 [handoff/README.md](C:/Users/HUAWEI/PycharmProjects/Skill-First-Hybrid-RAG/notes/monitoring/handoff/README.md)
2. 再读 [phase1_plan.md](C:/Users/HUAWEI/PycharmProjects/Skill-First-Hybrid-RAG/notes/monitoring/phase1_plan.md)
3. 如需落代码，再回看：
   - `backend/graph/agent.py`
   - `backend/workflow/orchestrated/execution_layer/engine/execution_layer.py`
   - `backend/context/assembly/context_manager.py`
