# Intent 测试与评估说明

## 一、目标

Intent 模块当前的评估不再只看“最后分类对不对”，而是按四层逐层评估：

```text
input -> evidence -> resolved -> control
```

也就是说，我们关心的不只是最终 route，而是：

- 输入是什么
- 规则层看到了什么
- resolver 收敛成了什么
- control 最终分到了哪里

---

## 二、当前测试范围

当前项目里有两类测试：

### 1. 单元测试

位于：

- [backend_test/intent](/C:/Users/HUAWEI/PycharmProjects/Skill-First-Hybrid-RAG/backend_test/intent)

当前覆盖：

- simple qa
- chat
- follow_up
- challenge
- ask_source
- system
- unsupported
- compound multi_question
- complex task
- control signal 映射
- evaluation 脚本基础功能

这些测试的作用是：

- 保证现有规则和 resolver 不被随意改坏
- 保证 control signal 映射稳定

### 2. 规则评估

位于：

- [evaluation/intent](/C:/Users/HUAWEI/PycharmProjects/Skill-First-Hybrid-RAG/evaluation/intent)

当前内容包括：

- 数据格式说明
- 种子数据
- 真实 query 标注模板
- 评估脚本

---

## 三、当前评估流程

当前规则评估流程是：

### 1. 准备评估样本

每条样本按四层结构标注：

- `input`
- `gold.evidence`
- `gold.resolved`
- `gold.control`

### 2. 用当前识别器跑 prediction

评估脚本会调用 `classify_intent()` 得到：

- `result.evidence`
- `result.resolved`
- `result.control`

### 3. 逐层比对

脚本当前按层比：

#### evidence 层

- `classifier_mode`
- `required_signals`
- `required_rule_ids`
- `dependency_signals`
- `unsupported_signals`

#### resolved 层

- `main_intent`
- `task.complexity`
- `task.shape`
- `context_dependency`

#### control 层

- `route`
- `mode`

### 4. 汇总输出

当前输出三部分：

- `overall`
- `per_batch`
- `rule_stats`

---

## 四、当前评分设计

## 4.1 overall

表示全体样本的分层准确率。

当前会输出：

- `evidence_mode_accuracy`
- `evidence_required_signals_accuracy`
- `evidence_required_rules_accuracy`
- `evidence_dependency_accuracy`
- `evidence_unsupported_accuracy`
- `resolved_main_intent_accuracy`
- `resolved_complexity_accuracy`
- `resolved_shape_accuracy`
- `resolved_context_accuracy`
- `control_route_accuracy`
- `control_mode_accuracy`

说明：

- 这是系统层面的整体表现
- 它反映的是“分层结果准确率”
- 不是规则逐条准确率

## 4.2 per_batch

表示按批次分别统计的分层准确率。

当前推荐批次：

- `simple_qa`
- `follow_up`
- `challenge`
- `ask_source`
- `system`
- `unsupported`
- `compound_multi_question`
- `complex_task`
- `ambiguous`

说明：

- 这是定位问题最重要的视角
- 因为总体平均数很容易掩盖某个批次的明显缺陷

## 4.3 rule_stats

表示逐条规则的命中统计。

当前这版已经开始做逐条规则统计，但仍是第一版。

当前已经能看到：

- 某条规则总共命中了多少次
- 某条规则在“被要求命中”的样本里是否命中了

当前还不够严格的地方：

- 还没有完整的 `tp / fp / fn`
- 还没有严格的 `precision / recall`

---

## 五、为什么还要继续加强 rule_stats

如果只看 `overall` 和 `per_batch`，你知道系统结果准不准，但不知道：

- 哪条规则值不值得保留
- 哪条规则经常误触发
- 哪条规则该加强，哪条该删掉

因此后续 `rule_stats` 应继续升级成：

- `hits`
- `tp`
- `fp`
- `fn`
- `precision`
- `recall`

这样我们才能真正做：

- 逐条规则调整
- 规则之间的取舍
- 是否要把某些批次交给模型

---

## 六、当前数据设计

当前已经有两类数据：

### 1. 种子集

- [seed_intent_eval_dataset.jsonl](/C:/Users/HUAWEI/PycharmProjects/Skill-First-Hybrid-RAG/evaluation/intent/seed_intent_eval_dataset.jsonl)

作用：

- 验证评估脚本可用
- 给当前规则一个 baseline
- 作为后续回归集

### 2. 真实 query 标注模板

- [real_query_annotation_template.jsonl](/C:/Users/HUAWEI/PycharmProjects/Skill-First-Hybrid-RAG/evaluation/intent/real_query_annotation_template.jsonl)

作用：

- 后续逐步替换成真实 query
- 按四层结构标注

原则：

- 真实 query 优先于手工样本
- 批次均衡优先于单纯扩大量

---

## 七、当前已经明确的边界

目前只做意图识别层。

因此以下内容不属于本轮重点：

- `agent.py` 执行流集成测试
- 多 query 拆分策略优化
- challenge claim 抽取
- challenge 验证 query 构造

原因：

- 它们已经进入执行流层
- 当前这一轮更重要的是把意图识别的结构和评估体系做稳定

---

## 八、建议的后续评估顺序

### 1. 先补真实 query

优先补：

- `follow_up`
- `compound_multi_question`
- `complex_task`
- `ambiguous`

因为这些最容易把规则打穿。

### 2. 再升级 rule_stats

补：

- `tp`
- `fp`
- `fn`
- `precision`
- `recall`

### 3. 最后再决定是否增加模型占比

规则评估完成后，再看：

- 哪些批次规则已经够用
- 哪些批次规则明显不足
- 是否值得把 `rule_plus_model` 和 `model_first_with_rule_guard` 的比重做大

---

## 九、一句话总结

当前 Intent 评估体系的核心不是只看最终 route，而是：

> 把每条样本拆成四层，逐层检查规则看到的 evidence、resolver 收敛结果和最终 control signal 是否都符合预期，再结合 batch 和 rule 维度定位问题。
