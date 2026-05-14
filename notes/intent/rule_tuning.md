# Intent Rule Tuning 记录

## 1. 文档目标

这份文档用于持续记录：

- 每轮规则优化改了什么
- 触发优化的症状是什么
- 当前哪些规则已可严格评估
- 哪些规则仍然只有 `hits` 或部分监督
- 接下来哪些优化还值得继续做

它不是架构总览，也不是评估脚本说明；
它更像是规则系统的手术记录和维护日志。

---

## 2. 当前调优原则

- 先看 `overall / per_batch / rule_stats`
- 先判断问题是在 `evidence`、`resolved` 还是 `control`
- 优先修高流量、高影响信号
- 不再为了追最后几个点无限堆专业词
- 新增规则尽量区分：
  - `global stable rules`
  - `group_shared / domain bootstrap rules`

---

## 3. 已完成的关键调优

### 3.1 结构重构

- 引入 `signal_buckets`
  - `intent`
  - `task`
  - `context`
  - `safety`
- 引入 `ContextSignals`
- 为 `resolved` / `control` 增加 grouped view

作用：

- 减少 `raw_signals` 混合池带来的理解负担
- 让规则解释、调试、训练导出更清楚

### 3.2 QA Rescue

新增或强化：

- `intent.qa.generic`
- `intent.qa.judgment`
- `intent.qa.judgment_clarify`
- `intent.qa.long_context_rescue`
- `intent.qa.long_form`

目标：

- 把掉进 `chat` 或误入 `clarify` 的普通 QA 拉回 `qa`
- 重点修复 `standard_qa` / `fuzzy_qa`

### 3.3 Challenge 提纯

新增区分：

- `hard challenge`
- `soft_doubt`

目标：

- 降低“求证”和“真正反驳”混淆
- 避免所有怀疑语气都强行进入 `challenge`

### 3.4 Long Case Shape 修复

新增策略：

- `verify / compare / summarize` 语义指纹
- 长文本尾部加权
- 长 query 的复杂 QA 保底

目标：

- 修复 `long_case_complex` 下 `shape` 长期失明的问题

### 3.5 规则资产分层

已完成：

- 将稳定规则与领域 bootstrap 规则分开理解
- 新增 [rule_assets.py](/C:/Users/HUAWEI/.codex/worktrees/2a18/Skill-First-Hybrid-RAG/backend/intent/rule_assets.py)
- 将 `domain bootstrap` 资产外提到 [domain_bootstrap_rules.json](/C:/Users/HUAWEI/.codex/worktrees/2a18/Skill-First-Hybrid-RAG/backend/intent/domain_bootstrap_rules.json)
- 为 `domain bootstrap` 资产补充版本、作用域、描述和变更记录结构

目标：

- 不再把专业词表误当成全局稳定规则
- 为后续动态调优 agent 留出配置接口

### 3.6 Meta-analysis QA 补强

已新增：

- “看代码解析 / 看规则怎么判断 query / 当前规则能不能判断” 这类问法的稳定模式

目标：

- 修复“表面简单但实际上是分析型 QA”的 query 掉进 `chat`

### 3.7 规则级监督准备

已完成：

- 新增 [rule_supervision.md](/C:/Users/HUAWEI/.codex/worktrees/2a18/Skill-First-Hybrid-RAG/notes/intent/rule_supervision.md)
- 新增 [rule_expectation_annotation_template.jsonl](/C:/Users/HUAWEI/.codex/worktrees/2a18/Skill-First-Hybrid-RAG/evaluation/intent/rule_expectation_annotation_template.jsonl)

目标：

- 让 `intent.qa.generic` / `intent.qa.judgment` / `challenge.soft_doubt` 从“只有 hits”过渡到“可严格评估”
- 把人工参与压缩到最小，只保留最终 true/false 裁决

---

## 4. 当前已知瓶颈

### 4.1 Evidence 仍是主瓶颈

当前最难的仍然是：

- 开放表达
- 隐式语义
- meta-style QA
- 边界模糊 query

这意味着：

- `resolved` 和 `control` 即使逻辑清楚，也会继承上游误差

### 4.2 规则层的天然边界

在不持续投入人工补规则的前提下，规则层的瓶颈主要体现在：

- 开放式表达覆盖有限
- 对知识域强依赖时容易膨胀成词表工程
- 对“表面简单、语义隐式”的 query 泛化弱

### 4.3 部分规则还不能严格评估

目前有些规则：

- 有 `hits`
- 但没有完整的 `expected_positive / expected_negative`

这意味着：

- 可以看活跃度
- 不能严格算 precision / recall / f1

典型待补监督对象：

- `intent.qa.generic`
- `intent.qa.judgment`
- `challenge.soft_doubt`

---

## 5. 规则层接下来还值得做什么

### 值得继续做

- 补小类样本分布
- 补规则级监督
- 继续清理 `domain bootstrap` 资产的配置承载
- 为训练集导出准备更稳定的标签结构

### 不再优先做

- 为了追最后几个点继续堆专业词
- 试图让规则层独自解决全部开放表达
- 在缺监督的情况下继续盲调新增规则

---

## 6. TODO

- [ ] 给 `intent.qa.generic` / `intent.qa.judgment` / `challenge.soft_doubt` 补规则级监督
- [ ] 补 `challenge` / `mixed_intent` / `fuzzy_qa` / `chat-meta boundary` 小类样本
- [ ] 为 `domain bootstrap` 配置增加版本化与变更记录
- [ ] 评估是否需要对 `resolver` / `control` 做小范围 layer-isolated eval
- [ ] 为后续 rule-maintenance agent 设计配置修改接口与审核流程
- [ ] 在开始 SFT 前，整理训练集导出字段与标签分层规范
