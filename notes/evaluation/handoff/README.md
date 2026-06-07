# Evaluation First Handoff

这个目录用于承接 `evaluation` 工作线。

当前这是一份**第一次交接文档**，定位是：

- 工作记忆
- 新对话启动入口
- 后续评测系统规划与实现的边界说明

它不是正式 benchmark 方案，也不是最终评测框架结论。

---

## 1. 这轮已经做了什么

当前仓库里，`evaluation` 还**没有**真正开始做质量评测系统。

已经先落下去的是一层共享事实层：

- `backend/observability/`

这层已经开始记录 `Workflow + 主回答模型` 相关的共享证据，目的是让后续评测系统不要直接耦合业务内部对象，而是基于统一证据层抽样、回放、打分。

当前已覆盖的事件：

- `workflow_run`
- `answer_model_run`
- `retrieval_run`
- `context_assembly_run`
- `compaction_run`
- `pre_compaction_extraction_run`

这意味着：

- 评测系统现在还没做
- 但它未来要消费的第一版证据底座已经有了

---

## 2. 当前认识

当前项目里，`evaluation` 不应该和 `monitoring` 混做。

三层关系已经明确：

### `observability`

给 `evaluation` 提供：

- trace
- event
- messages 摘要
- retrieval 摘要
- compaction / extraction 事实

### `evaluation`

在这些事实之上做：

- 质量判断
- bad case 归档
- 回归评测
- 人工标注或自动 grader

### `monitoring`

关注的是：

- 运行健康
- 性能
- 异常

不是：

- 回答正确性
- retrieval 好不好
- compaction 是否保真

所以当前共识是：

- `evaluation` 是判断层
- `observability` 是事实层
- `evaluation` 不应重新设计一套与 `observability` 脱节的数据模型

---

## 3. 当前最值得评的范围

用户已经明确：

- 这阶段先不做 intent 层
- 先从 `Workflow + 主回答模型` 做起

因此 `evaluation` 第一阶段最值得评的不是全部系统，而是下面三块。

### A. Retrieval 评测

关注：

- 这次回答前是否取到了合适证据
- `knowledge` / `memory` 命中是否足够
- 命中证据是否真的被 answer path 用到

第一阶段建议评的问题：

- 有没有 evidence
- evidence 数量是否过少
- evidence 来源是否合理
- retrieval hit 是否明显偏题

### B. 主回答评测

关注：

- 最终回答是否 grounded
- 是否遵守 evidence / workflow 约束
- 是否明显编造
- 是否回答了当前 query

第一阶段建议评的问题：

- answer 是否引用了可见依据
- answer 是否与 retrieval/context 冲突
- answer 是否遗漏关键要求

### C. Memory / Compaction 保真评测

这是当前项目一个非常关键、也很有特色的点。

关注：

- compaction 前被裁掉的内容，是否通过 pre-compaction extraction 得到了合理保留
- `daily_log` / `domain_case` 命中后，是否保留了足够的历史锚点
- `core` 注入是否真的起到了稳定规则作用

这块后续很可能会成为独立评测专题。

---

## 4. 当前已经可用的评测证据

后续做 `evaluation` 时，可优先消费这些入口的事实。

### 主回答入口

- `backend/graph/agent.py`

可用证据：

- `answer_model_run`
- messages 摘要
- workflow payload 摘要
- retrieval block 摘要

### Workflow 执行层

- `backend/workflow/orchestrated/execution_layer/engine/execution_layer.py`

可用证据：

- `workflow_run`
- unit 结果
- key events
- evidence summary

### Context 组装层

- `backend/context/assembly/context_manager.py`

可用证据：

- `context_assembly_run`
- `core` block / `retrieved_memories` block 存在性
- `compaction_run`
- `pre_compaction_extraction_run`
- slice 边界

这些已经足够支持第一版：

- bad case 采样
- compaction 保真回放
- retrieval / answer 关联复盘

---

## 5. 评测系统建议先做的三大模块

### A. Retrieval Evaluation

目标：

- 判断 retrieval 是否提供了可用证据

第一阶段建议输出：

- `good / weak / bad`
- 缺证据 / 偏题 / 来源过窄 / hits 为空

输入优先来自：

- `retrieval_run`
- `workflow_run.evidence_summary`

### B. Answer Evaluation

目标：

- 判断最终回答是否 grounded、是否回答到点上

第一阶段建议输出：

- `grounded / partially_grounded / ungrounded`
- `answered / partially_answered / missed`

输入优先来自：

- `answer_model_run`
- `workflow_run`
- `retrieval_run`

### C. Memory / Compaction Preservation Evaluation

目标：

- 判断 memory 命中与 compaction/extraction 是否保住了关键历史信息

第一阶段建议输出：

- pre-compaction extraction 是否覆盖到应保留 slice
- compaction 后是否还能恢复到足够上下文
- memory 命中是否只剩 summary，还是还能指回历史锚点

这部分是项目差异化价值之一，建议高度重视。

---

## 6. 第一阶段目标

第一次正式做 `evaluation` 时，建议目标先收窄到：

1. 能从共享证据层抽样真实请求
2. 能对 `retrieval / answer / compaction-preservation` 做最小三分法判断
3. 能形成第一版 bad case 列表
4. 能把 bad case 回链到同一条 trace

先不要把目标设成：

- 大规模离线 benchmark
- 自动奖励模型
- 复杂多 grader ensemble
- 全面历史回放平台

---

## 7. 约束

后续实现 `evaluation` 时，建议继续遵守这些约束：

### 不重造事实层

- 不要自己再定义一套和 `observability` 平行的事件结构
- `evaluation` 应消费共享证据，而不是绕过它直读业务内部所有对象

### 先用摘要证据，不急着上全量原文

当前共享证据层刻意是轻量的：

- 不存全量 prompt
- 不存全量 transcript
- 不存全量 retrieval candidates 正文

评测第一阶段应先验证：

- 这些摘要证据够不够支撑打分

只有不够时，再讨论是否扩字段。

### 不和 monitoring 混模块

- `evaluation` 只做质量判断
- 不负责告警、SLA、性能面板

### 不扩到 intent

这阶段先不评 intent。

优先顺序固定为：

- Workflow
- 主回答模型
- retrieval
- context / compaction / memory extraction

---

## 8. 当前不做什么

这个目录当前不承诺：

- 运行态健康判断
- 性能诊断
- 实时异常发现
- dashboard / alert

这些属于 `monitoring`。

---

## 9. 建议的新对话起手式

如果下一次单独开一个对话做评测系统，建议直接从下面问题开始：

1. 第一阶段先评 retrieval、answer、还是 compaction-preservation？
2. 目前 `observability` 的摘要字段是否足够支持这些评测？
3. 第一版评测先做人审规则、程序规则，还是 LangSmith eval 风格 grader？
4. bad case 的最小归档格式是什么？

---

## 10. 一句话收口

当前 `evaluation` 的正确起点不是直接造一个大评测框架，而是**基于已经落下去的 `backend/observability/` 共享证据层，先把 Workflow + 主回答模型这条链的 retrieval / answer / memory-compaction 保真三类评测做起来**。
