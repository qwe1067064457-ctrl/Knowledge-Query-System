# Rule Supervision Guide

## 1. 文档目标

这份文档用于说明：

- 为什么部分规则目前还不能严格评估
- 规则级监督应该怎么补
- 哪些规则优先补
- 人工参与应该裁决什么，不需要裁决什么

---

## 2. 什么叫“规则级监督”

规则级监督不是只标：

- 这条 query 属于什么 batch
- 最后 route 对不对

它还要标：

- 某条规则对这条样本来说，是否**应该命中**

也就是：

- `expected_positive = true`
- 或 `expected_negative = false`

只有这样，评估脚本才能为该规则计算：

- `precision`
- `recall`
- `f1`

如果只有 `hits`，那只能看活跃度，不能看质量。

---

## 3. 当前优先补的规则

### 3.1 `intent.qa.generic`

补它的原因：

- 它已经承担了很多 QA Rescue 工作
- 但目前在 summary 里还只有 `hits`
- 没有完整的 `expected_positive / expected_negative`

标注时判断标准：

- 用户是否在发起通用问答请求
- 是否存在明确求解、求解释、求处理、求条件、求后果的问法
- 不要求一定带法律/医疗等领域词

### 3.2 `intent.qa.judgment`

补它的原因：

- 它对 `fuzzy_qa` 很关键
- 会直接影响 `qa` 与 `chat/clarify` 的边界

标注时判断标准：

- 用户是否在问“是否构成 / 是否成立 / 是否合理 / 是否违法 / 是否有责任”
- 这是判断型 QA，不是单纯情绪表达，不是 ask_source

### 3.3 `challenge.soft_doubt`

补它的原因：

- 目前 challenge 提纯已经拆出了 `soft_doubt`
- 但没有足够规则级监督

标注时判断标准：

- 是否属于轻质疑、求证、保留态度
- 通常需要结合上一轮回答看
- 不能把所有带“是不是 / 确定吗”的句子都标成它

---

## 3.4 本轮 review 后的两个澄清

### 澄清 1：`judgment` 与“是否需要上文”不是同一个判断

例如：

- `这样算医疗事故吗？`

这类 query 在真实对话中常常**需要更多上下文**或后续澄清；
但这不影响它在规则级监督里被标为：

- `intent.qa.judgment = true`

因为这里判断的是：

- 这条规则是否应该命中

而不是：

- 最后是否应该直接回答
- 是否需要 `needs_clarification`

### 澄清 2：`follow_up` 和 `challenge` 存在表面重叠，但不是同一语义轴

它们的差别是：

- `follow_up`
  - 更偏上下文依赖
  - 回答“这句话是不是在接上文”
- `challenge / soft_doubt`
  - 更偏立场或态度
  - 回答“这句话是不是在质疑、保留、反驳上一轮说法”

因此：

- 它们在表面表达上可能重叠
- 甚至可能在某些样本中共存
- 但监督时应分开裁决

### 澄清 3：普通 QA 可以带不确定语气，但不等于 `soft_doubt`

例如：

- `这种规则是不是全国都适用？`

它可以带有轻微不确定语气；
但如果没有上一轮回答、也没有明显在质疑某个既有说法，当前监督口径仍应标：

- `challenge.soft_doubt = false`

否则会把大量普通 QA 错误吸进 challenge 语义。

---

## 4. 建议的人机分工

### 系统先做

- 生成候选样本
- 组织 JSONL 模板
- 提供 target rule id
- 提供初始 rationale
- 汇总待标注批次

### 人工只做

- 判断这条样本对目标规则是 `true` 还是 `false`
- 必要时改一句理由
- 标记是否需要讨论

这意味着人工不需要：

- 从零设计 schema
- 手工拼测试数据格式
- 自己统计 precision / recall

---

## 5. 当前建议的最小人工参与方式

当前最小参与就够：

1. 先只看 `intent.qa.generic`
2. 再看 `intent.qa.judgment`
3. 最后看 `challenge.soft_doubt`

每条只需要：

- `expected = true/false`
- 一句理由

如果有争议，再额外加：

- `notes`

这已经足够让评估脚本开始算质量。

---

## 6. 模板位置

当前模板文件：

- [rule_expectation_annotation_template.jsonl](/C:/Users/HUAWEI/.codex/worktrees/2a18/Skill-First-Hybrid-RAG/evaluation/intent/rule_expectation_annotation_template.jsonl)
- [rule_expectation_review_list.md](/C:/Users/HUAWEI/.codex/worktrees/2a18/Skill-First-Hybrid-RAG/evaluation/intent/rule_expectation_review_list.md)

建议流程：

1. 复制模板或基于模板扩展样本
2. 补 `expected`
3. 标 `review_status`
4. 汇总回评估数据集

---

## 7. 当前监督进度

当前 [rule_expectation_annotation_template.jsonl](/C:/Users/HUAWEI/.codex/worktrees/2a18/Skill-First-Hybrid-RAG/evaluation/intent/rule_expectation_annotation_template.jsonl) 已扩到：

- `intent.qa.generic`：12 条
- `intent.qa.judgment`：12 条
- `challenge.soft_doubt`：12 条

其中：

- 当前 36 条都已完成人工裁决
- `approved` 33 条，`approved_with_note` 3 条
- 现在这 36 条都会被评估脚本计入外部规则监督

此外，已新增一份正式的合并监督资产：

- [rule_supervision_approved_v1.jsonl](/C:/Users/HUAWEI/.codex/worktrees/2a18\Skill-First-Hybrid-RAG/evaluation/intent/rule_supervision_approved_v1.jsonl)

这份文件包含：

- 现有 36 条 approved 规则监督
- `seed_query_20260514_gold_v1` 扁平化后的 45 条规则监督

合计：

- `81` 条可直接用于 `rule_stats` 的严格监督条目

基于这 `81` 条严格监督，当前阶段性结果为：

- `intent.qa.generic`
  - `precision = 0.7692`
  - `recall = 0.8333`
  - `f1 = 0.8`
- `intent.qa.judgment`
  - `precision = 1.0`
  - `recall = 1.0`
  - `f1 = 1.0`
- `challenge.soft_doubt`
  - `precision = 1.0`
  - `recall = 1.0`
  - `f1 = 1.0`

其中本轮最重要的结论是：

- `judgment` 和 `soft_doubt` 在更长、更自然、更接近真实对话的样本上已经明显提升
- 规则级监督的价值已经从“确认规则是否可评估”进入“确认规则是否真的在泛化”阶段
