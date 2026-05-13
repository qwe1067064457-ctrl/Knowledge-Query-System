# Intent 测试与评估说明

## 1. 文档目标

这份文档用于说明当前 `intent` 模块是如何测试、如何评估、以及现阶段哪些指标已经具备、哪些还只是第一版。

当前评估不再只看“最后分流对不对”，而是按四层结构逐层检查：

```text
input -> evidence -> resolved -> control
```

这四层分别回答：

- `input`：系统拿到的原始输入是什么
- `evidence`：规则层和证据层看到了什么
- `resolved`：resolver 最终收敛成了什么意图结果
- `control`：最后把请求分到哪条粗执行流

这也是当前整个测试与评估体系的主线。

---

## 2. 当前测试分层

当前测试分为两类：

### 2.1 单元测试

位置：

- [C:\Users\HUAWEI\PycharmProjects\Skill-First-Hybrid-RAG\backend_test\intent\test_intent_classifier.py](/C:/Users/HUAWEI/PycharmProjects/Skill-First-Hybrid-RAG/backend_test/intent/test_intent_classifier.py)
- [C:\Users\HUAWEI\PycharmProjects\Skill-First-Hybrid-RAG\backend_test\intent\test_control_signal.py](/C:/Users/HUAWEI/PycharmProjects/Skill-First-Hybrid-RAG/backend_test/intent/test_control_signal.py)
- [C:\Users\HUAWEI\PycharmProjects\Skill-First-Hybrid-RAG\backend_test\intent\test_rule_confidence.py](/C:/Users/HUAWEI/PycharmProjects/Skill-First-Hybrid-RAG/backend_test/intent/test_rule_confidence.py)
- [C:\Users\HUAWEI\PycharmProjects\Skill-First-Hybrid-RAG\backend_test\intent\test_intent_evaluation_script.py](/C:/Users/HUAWEI/PycharmProjects/Skill-First-Hybrid-RAG/backend_test/intent/test_intent_evaluation_script.py)

作用：

- 保护规则识别逻辑不被无意改坏
- 保护 resolver 的收敛逻辑
- 保护 `control signal` 的粗分流映射
- 验证规则版 `confidence` 的计算流程
- 验证评估脚本输出结构

### 2.2 规则评估

位置：

- [C:\Users\HUAWEI\PycharmProjects\Skill-First-Hybrid-RAG\evaluation\intent\README.md](/C:/Users/HUAWEI/PycharmProjects/Skill-First-Hybrid-RAG/evaluation/intent/README.md)
- [C:\Users\HUAWEI\PycharmProjects\Skill-First-Hybrid-RAG\evaluation\intent\dataset_schema.md](/C:/Users/HUAWEI/PycharmProjects/Skill-First-Hybrid-RAG/evaluation/intent/dataset_schema.md)
- [C:\Users\HUAWEI\PycharmProjects\Skill-First-Hybrid-RAG\evaluation\intent\seed_intent_eval_dataset.jsonl](/C:/Users/HUAWEI/PycharmProjects/Skill-First-Hybrid-RAG/evaluation/intent/seed_intent_eval_dataset.jsonl)
- [C:\Users\HUAWEI\PycharmProjects\Skill-First-Hybrid-RAG\evaluation\intent\real_query_annotation_template.jsonl](/C:/Users/HUAWEI/PycharmProjects/Skill-First-Hybrid-RAG/evaluation/intent/real_query_annotation_template.jsonl)
- [C:\Users\HUAWEI\PycharmProjects\Skill-First-Hybrid-RAG\evaluation\intent\evaluate_intent_rules.py](/C:/Users/HUAWEI/PycharmProjects/Skill-First-Hybrid-RAG/evaluation/intent/evaluate_intent_rules.py)

作用：

- 对当前规则系统做分层评估
- 观察不同批次的掉点位置
- 为后续是否增加模型占比提供依据

---

## 3. 当前单元测试覆盖了什么

### 3.1 `test_intent_classifier.py`

当前主要覆盖：

- `simple_qa`
  - 正例：典型法律知识问答应识别为 `qa + simple + single_question`
- `chat`
  - 正例：问候、寒暄应识别为 `chat`
- `follow_up`
  - 正例：有历史时短追问应识别出 `follow_up`
  - 反例：无足够上下文时不应盲目高置信追问
- `challenge`
  - 正例：有上一轮回答时“你确定吗”应进入 challenge
  - 反例：没有历史时应更偏向 `needs_clarification`
- `ask_source`
  - 正例：有历史时“依据是什么”应命中 `ask_source`
- `system`
  - 正例：问系统能力应识别为 `system`
- `unsupported`
  - 正例：自然语言删除知识库文件应识别为 `unsupported`
- `compound_multi_question`
  - 正例：一句话多个独立问题应识别为 `compound + multi_question`
- `complex_task`
  - 正例：对比、整理、表格类请求应识别为 `complex`

此外，它还会检查：

- `evidence.rule_confidence` 是否被正确挂入结果
- `resolved` 是否按预期收敛
- `control` 是否映射到正确主路由

### 3.2 `test_control_signal.py`

当前主要验证 `ResolvedIntent -> ControlSignal` 的粗分流映射是否稳定：

- `simple qa -> rag`
- `follow_up qa -> rag + rewrite`
- `challenge qa -> rag + challenge + force_citation`
- `system -> direct + capability`
- `compound multi_question -> rag + decompose_query`
- `complex task -> agent + use_planner`
- `unsupported -> reject`

### 3.3 `test_rule_confidence.py`

这一组测试专门验证规则版 `confidence` 的四个核心步骤：

#### 分类 1：单条规则基础分

- 正例：单条高强规则命中后应保持高置信

#### 分类 2：同类 signal 聚合

- 正例：同一个 signal 被多条规则支持时，应得到 `support bonus`

#### 分类 3：冲突惩罚

- 正例：`qa` 与 `chat` 同时命中时，应触发冲突惩罚

#### 分类 4：上下文修正

- 正例：缺失上下文时，`follow_up` 的置信度应下降

这部分测试对应的不是“真实准确率”，而是：

> 当前规则版 confidence 的计算逻辑是否按设计执行。

### 3.4 `test_intent_evaluation_script.py`

这一组测试验证评估脚本自身是否正常工作，重点不是业务准确率，而是：

- 脚本能否正确读取数据集
- 是否按约定输出 `overall / per_batch / rule_stats`
- 输出字段是否完整

---

## 4. 评估数据是如何组织的

当前评估数据采用四层结构。推荐格式见：

- [C:\Users\HUAWEI\PycharmProjects\Skill-First-Hybrid-RAG\evaluation\intent\dataset_schema.md](/C:/Users/HUAWEI/PycharmProjects/Skill-First-Hybrid-RAG/evaluation/intent/dataset_schema.md)

顶层结构如下：

```json
{
  "id": "sample_001",
  "batch": "simple_qa",
  "input": {},
  "gold": {
    "evidence": {},
    "resolved": {},
    "control": {}
  },
  "notes": ""
}
```

### 4.1 `input`

只记录真实输入：

- `user_query`
- `history`

这里不要求手工填写 `context_state`，因为实际代码会由 `history` 推导。

### 4.2 `gold.evidence`

这一层不是要求把所有证据穷举出来，而是标注“最低限度必须识别出来的关键 evidence”。

当前主要字段：

- `classifier_mode`
- `required_signals`
- `required_rule_ids`
- `rule_expectations`
- `dependency_signals`
- `unsupported_signals`

### 4.3 `gold.resolved`

这一层描述 resolver 最终应该收敛成什么。

当前主要字段：

- `main_intent`
- `modifiers`
- `task.complexity`
- `task.shape`
- `context_dependency`

### 4.4 `gold.control`

这一层只描述粗分流结果，不描述执行流细节。

当前主要字段：

- `route`
- `mode`

---

## 5. 当前评估流程

当前评估脚本的流程可以概括为：

```text
准备四层标注样本
  ↓
运行当前 classify_intent()
  ↓
得到 prediction.evidence / prediction.resolved / prediction.control
  ↓
逐层和 gold 对比
  ↓
输出 overall / per_batch / rule_stats
```

也就是说，现在不是只看“最后 route 对不对”，而是逐层检查：

- evidence 是否识别出了必要信号
- resolver 是否收敛正确
- control 是否把请求送进了正确粗执行流

### 5.1 当前 summary 的口径澄清

当前 `overall` 和 `per_batch` 都属于：

- 端到端链路一致性评估

它们评估的是：

- `input -> evidence -> resolved -> control`

整条真实流水线跑完后的最终表现，而不是某一层的纯能力上限。

它的优点是：

- 最接近真实上线行为
- 能快速看出哪个 batch 最容易掉点
- 能观察规则层改动是否真的改善最终分流

它的边界是：

- `resolved` 和 `control` 的错误会继承上游 `evidence` 的误差
- 因此不能直接把端到端结果等同为“后层纯能力评估”

### 5.2 当前还没有系统化做的评估

当前还没有全面铺开的，是：

- layer-isolated eval

它指的是：

- 给 `resolver` 喂金标 `evidence`
- 单独评估 `resolved`
- 给 `control` 喂金标 `resolved`
- 单独评估 `control`

暂时没有全面做这件事，主要原因不是实现困难，而是：

- 中间层金标构造成本高
- 很多中间层标签带策略解释色彩
- 现阶段更需要先稳定端到端评估和数据结构

因此当前建议是：

- 继续以端到端评估为主
- 只在关键问题上做少量 layer-isolated 切片验证

---

## 6. 当前评估输出解释

### 6.1 `overall`

表示全体样本上的分层准确率。

当前脚本会输出：

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

这部分衡量的是：

> 系统分层结果整体准不准。

它不是规则逐条精确率。

### 6.2 `per_batch`

表示按批次分开的分层准确率。

当前建议批次包括：

- `simple_qa`
- `follow_up`
- `challenge`
- `ask_source`
- `system`
- `unsupported`
- `compound_multi_question`
- `complex_task`
- `ambiguous`

这部分最重要的价值是帮助定位：

- 哪个批次最容易掉点
- 哪个批次最可能需要模型补强

因为总体平均值很容易掩盖局部问题。

### 6.3 `rule_stats`

当前 `rule_stats` 已经升级为严格版。

当前能看到：

- `hits`
- `required_hits`
- `required_hit_rate`
- `labeled_samples`
- `expected_positive`
- `expected_negative`
- `tp`
- `fp`
- `fn`
- `tn`
- `precision`
- `recall`
- `accuracy`
- `f1`

但要注意前提：

- 只有写进 `gold.evidence.rule_expectations` 的规则，才会参与该样本的严格统计
- 没有标注的规则，不会被默认当成负例

---

## 7. 每一层的准确率是如何计算的

### 7.1 evidence 层

当前 evidence 层分为 5 个子项：

- `evidence_mode_accuracy`
  - 判断 `result.evidence.classifier_mode == gold.evidence.classifier_mode`
- `evidence_required_signals_accuracy`
  - 判断 `gold.evidence.required_signals` 是否是 `result.evidence.raw_signals` 的子集
- `evidence_required_rules_accuracy`
  - 判断 `gold.evidence.required_rule_ids` 是否是实际命中规则 ID 的子集
- `evidence_dependency_accuracy`
  - 逐键比较 `dependency_signals`
- `evidence_unsupported_accuracy`
  - 逐键比较 `unsupported_signals`

每条样本在每个子项上只有“对 / 错”两种结果。

最终准确率计算方式：

```text
该子项正确样本数 / 总样本数
```

### 7.2 resolved 层

当前 resolved 层分为 4 个子项：

- `resolved_main_intent_accuracy`
- `resolved_complexity_accuracy`
- `resolved_shape_accuracy`
- `resolved_context_accuracy`

每项都按：

```text
正确样本数 / 总样本数
```

计算。

### 7.3 control 层

当前 control 层分为 2 个子项：

- `control_route_accuracy`
- `control_mode_accuracy`

同样按：

```text
正确样本数 / 总样本数
```

计算。

### 7.4 rule_stats 层

当前 `rule_stats` 的严格评估依赖：

- `gold.evidence.rule_expectations`

对每条被标注的规则，逐样本判断：

- 期望命中且实际命中 -> `tp`
- 期望命中但实际未命中 -> `fn`
- 期望不命中但实际命中 -> `fp`
- 期望不命中且实际未命中 -> `tn`

然后计算：

```text
precision = tp / (tp + fp)
recall = tp / (tp + fn)
accuracy = (tp + tn) / labeled_samples
f1 = 2 * precision * recall / (precision + recall)
```

---

## 8. 当前规则版 confidence 在测试中的位置

规则版 `confidence` 的设计与说明详见：

- [C:\Users\HUAWEI\PycharmProjects\Skill-First-Hybrid-RAG\notes\intent\intent_rule_confidence.md](/C:/Users/HUAWEI/PycharmProjects/Skill-First-Hybrid-RAG/notes/intent/intent_rule_confidence.md)

在当前测试体系里，它主要处于两种位置：

### 8.1 单元测试位置

验证计算逻辑是否正确：

- 单条规则基础分
- 同类 signal 聚合
- 冲突惩罚
- 上下文修正

### 8.2 resolver 辅助位

当前 `rule_confidence` 也会被挂入 `evidence`，并在 resolver 的 `decision.strength` 里作为参考信号之一。

需要特别注意：

- 当前 `rule_confidence` 不是统计概率
- 当前 `rule_confidence` 不是规则真实 precision
- 它是工程上的“规则证据强度”

所以现阶段我们测试的是：

> 这套强度计算是否按设计执行。

而不是：

> 它是否已经能代表真实世界中的规则准确率。

---

## 9. 当前数据集的边界

### 9.1 种子集

文件：

- [C:\Users\HUAWEI\PycharmProjects\Skill-First-Hybrid-RAG\evaluation\intent\seed_intent_eval_dataset.jsonl](/C:/Users/HUAWEI/PycharmProjects/Skill-First-Hybrid-RAG/evaluation/intent/seed_intent_eval_dataset.jsonl)

作用：

- 验证评估脚本可用
- 为当前规则提供一个 baseline
- 作为后续回归样本起点

边界：

- 这批种子样本主要是为当前结构和当前实现对齐的
- 它适合做结构校验和回归起点
- 它不等于真实用户分布

所以即使种子集结果很好，也不能直接说明规则已经足够强。

### 9.2 真实 query 模板

文件：

- [C:\Users\HUAWEI\PycharmProjects\Skill-First-Hybrid-RAG\evaluation\intent\real_query_annotation_template.jsonl](/C:/Users/HUAWEI/PycharmProjects/Skill-First-Hybrid-RAG/evaluation/intent/real_query_annotation_template.jsonl)

作用：

- 后续逐步替换成真实 query
- 用真实数据验证规则边界

当前优先建议补的批次：

- `follow_up`
- `compound_multi_question`
- `complex_task`
- `ambiguous`

这些批次最容易把当前规则打穿。

---

## 10. 当前边界：只做意图识别，不做执行流优化

当前这轮工作的边界很明确：只做意图识别层的测试与评估。

因此以下内容不属于这份文档的核心范围：

- `agent.py` 的执行流集成测试
- 多 query 拆分策略优化
- challenge claim 抽取
- challenge 验证 query 构造

原因是这些都已经进入执行流层，而当前更重要的是把：

- 四层结构
- 分层测试
- 分层评估
- 规则统计

先稳定下来。

---

## 11. 建议的后续评估顺序

### 分类 1：先补真实 query

优先补：

- `follow_up`
- `compound_multi_question`
- `complex_task`
- `ambiguous`

### 分类 2：继续扩大严格规则标注

当前 `rule_stats` 已经具备严格统计能力，后续重点不再是补字段，而是：

- 扩大 `rule_expectations` 覆盖面
- 让更多真实 query 进入严格统计
- 观察哪些规则在真实样本上开始出现 `fp / fn`

### 分类 3：最后再决定模型占比

先看真实规则评估结果，再决定是否要扩大：

- `rule_plus_model`
- `model_first_with_rule_guard`

的使用范围。

---

## 12. 一句话总结

当前 Intent 测试与评估体系的核心不是只看最终 `route`，而是：

> 把每条样本拆成 `input -> evidence -> resolved -> control` 四层，逐层检查规则看到了什么、resolver 收敛成了什么、最终 control 是否分流正确，再结合 batch 和 rule 维度定位问题。
