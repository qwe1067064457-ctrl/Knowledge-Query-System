# Monitoring First Handoff

这个目录用于承接 `monitoring` 工作线。

当前这是一份**第一次交接文档**，定位是：

- 工作记忆
- 新对话启动入口
- 后续监测系统规划与实现的边界说明

它不是正式方案文档，也不是最终架构结论。

---

## 1. 这轮已经做了什么

当前仓库里，`monitoring` 还**没有**真正开始做运行态健康系统。

已经先落下去的是一层更底的共享事实层：

- `backend/observability/`

这层现在已经接进了 `Workflow + 主回答模型` 主链，负责产生统一的运行事实与共享证据。

当前已经能采到这些事件：

- `workflow_run`
- `answer_model_run`
- `retrieval_run`
- `context_assembly_run`
- `compaction_run`
- `pre_compaction_extraction_run`

当前实现特点：

- `LangSmith-first`
- 未配置 LangSmith 时安全降级为 no-op
- 先保留统一 schema / metadata / trace context
- 暂时不做 dashboard、告警、聚合分析

也就是说：

- `observability` 已经开始做
- `monitoring` 还没有开始做

---

## 2. 当前认识

当前项目里，三层边界已经明确：

### `observability`

职责：

- 事实采集
- 共享证据
- 统一 trace / run / metadata

它回答的是：

- 这次请求实际发生了什么
- 走了哪些阶段
- 用了哪些证据
- compaction / extraction / retrieval / answer 发生了什么

### `monitoring`

职责：

- 运行态健康
- 性能
- 稳定性
- 异常与退化

它回答的是：

- 哪一步慢
- 哪一步失败
- 哪条链路不稳定
- 哪类请求最近异常增多

### `evaluation`

职责：

- 质量判断
- 回答质量
- retrieval 质量
- memory / compaction 保真度

它回答的是：

- 结果好不好
- 命中准不准
- 回答是否 grounded
- compaction 后是否丢失关键信息

当前共识是：

- `monitoring` 不和 `evaluation` 混做
- 两者都消费 `observability`
- `observability` 是底座，不做高层健康判断

---

## 3. 当前已经可用的共享证据

如果后续要做监测系统，当前可优先消费的事实来自这些代码入口：

### 主回答入口

- `backend/graph/agent.py`

当前已接入：

- 根 trace context
- `answer_model_run`
- workflow payload 摘要
- retrieval 摘要

### Workflow 执行层

- `backend/workflow/orchestrated/execution_layer/engine/execution_layer.py`

当前已接入：

- `workflow_run`
- unit 执行结果摘要
- evidence summary
- key events

### Context 组装层

- `backend/context/assembly/context_manager.py`

当前已接入：

- `context_assembly_run`
- `compaction_run`
- `pre_compaction_extraction_run`
- `core` / `retrieved_memories` block 存在性

---

## 4. 监测系统建议先做的三大模块

后续如果开新对话开始做 `monitoring`，建议先按下面三块拆。

### A. Workflow / 主回答运行监测

关注：

- 一次请求走了哪个 route
- workflow 是否正常产出 `ExecutionPayload`
- 主回答模型最终是否成功完成
- 主回答耗时
- reject / respond / knowledge_orchestrator / agent 分布

建议第一批关注指标：

- 请求总数
- route 分布
- action 分布
- answer 成功率
- answer latency
- 主回答 fallback 比例

### B. Retrieval / Context / Compaction 运行监测

关注：

- retrieval 是否发生
- retrieval 命中量
- `core` block 是否注入
- `retrieved_memories` block 是否注入
- compaction 是否触发
- pre-compaction extraction 是否成功

建议第一批关注指标：

- retrieval run rate
- memory hit rate
- compaction rate
- pre-compaction extraction success rate
- compaction skipped / failed rate

### C. Build / Memory Build 运行监测

这块当前不要求马上做，但后续会需要。

关注：

- knowledge build 状态
- memory versioned build 状态
- build validate / activate 失败
- pre-compaction extraction 是否带来写入异常

当前这块可以先留在第二阶段。

---

## 5. 监测系统第一阶段目标

第一次正式做 `monitoring` 时，建议目标不要太大，先做到：

1. 能按 `trace_id / session_id / query_id` 回看一次主回答请求
2. 能看到 `workflow -> context -> retrieval -> answer` 的最小事实链
3. 能看出 compaction / pre-compaction extraction 是否发生以及是否失败
4. 能按 route / action / status 做最小聚合
5. LangSmith 未开启时，系统仍然不影响主业务

先不要把目标设成：

- 完整告警系统
- 全量 dashboard
- 长期统计面板
- 自动异常归因

---

## 6. 约束

后续实现 `monitoring` 时，建议继续遵守这些约束：

### 事实与判断分离

- `observability` 只产事实
- `monitoring` 再做健康判断
- 不要把“质量差”“系统异常”这种结论直接塞回事实层 schema

### 不反向污染主链

- tracing / monitoring 失败不能影响主回答
- 不要让 dashboard 需要的字段反过来重塑业务 contract

### 先轻后重

第一阶段优先：

- trace 浏览
- 简单聚合
- 错误与性能观察

不要一开始就做：

- 告警编排
- 多租户监控面板
- 复杂统计仓

### 不扩到 intent 层

当前用户已经明确：

- 这阶段不先做 intent 层

所以监测系统第一轮只围绕：

- Workflow
- 主回答模型
- retrieval
- context
- compaction
- pre-compaction extraction

---

## 7. 当前不做什么

这个目录当前不承诺：

- 质量评分
- retrieval 准确率判断
- 答案好坏判断
- 人工标注流

这些属于 `evaluation`。

---

## 8. 建议的新对话起手式

如果下一次单独开一个对话做监测系统，建议直接从下面问题开始：

1. 我们第一阶段要看哪些运行健康问题？
2. 这些问题分别消费哪些 `observability` 事件？
3. 第一批是只做 LangSmith 视图，还是要补内部 analyzer/service？
4. 哪些指标只要 trace 聚合，哪些需要新增业务事件？

---

## 9. 一句话收口

当前 `monitoring` 的正确起点不是重新定义事实层，而是**基于已经落下去的 `backend/observability/` 共享证据层，做 Workflow + 主回答链的运行态健康系统**。
