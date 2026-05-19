# Intent 项目说明

## 1. 当前定位

这一条线现在更准确的名字不是“传统 intent 分类”，而是：

- `request understanding`

它的职责不是直接回答问题，也不是提前替后续执行流做完整决策，而是：

- 理解用户请求属于什么语义域
- 给出任务画像
- 给出上下文事实与理解缺口
- 给出安全/越界边界
- 产出可被后续 `control` 消费的稳定 `resolved` 结果

当前我们明确坚持：

- `rule-lite + model-centric understanding`

这意味着：

- rule 层保留 baseline、hard gate、teacher、regression anchor 的价值
- 但不再让 rule 层继续扩大成半个 workflow 决策器

## 2. 当前主链

当前 understanding 主链仍按四层理解：

```text
input -> evidence -> resolved -> control
```

其中：

### `input`

系统拿到的原始请求与上下文输入。

当前主要包括：

- `user_query`
- `context_state`
- `model_context`

### `evidence`

对请求做第一轮结构化观察。

当前 `V2` 正式骨架只保留四大语义类：

- `intent`
- `task`
- `context`
- `safety`

对应 resolver 的主消费结构主要是：

- `candidate_intents`
- `task_candidates`
- `context_signals`
- `unsupported_signals`

### `resolved`

把 `evidence` 收敛成稳定的理解结果。

当前重点包括：

- `main_intent`
- `modifiers`
- `task.complexity`
- `task.shape`
- `task.topology`
- `ambiguity_state`
- `context_dependency`

### `control`

把稳定的 understanding 结果映射为粗粒度执行控制。

当前状态：

- 已完成一版最小 `control v2` 收口
- 正式结构收为：
  - `route`
  - `handling_mode`
  - `capabilities`
  - `trace`
- 但仍保留旧兼容导出
- 真正的 workflow 消费迁移仍未完成

## 3. 当前 V2 已经完成到哪

### 3.1 `evidence v2` 已基本站稳

当前正式 schema 已经去掉或退场了这些旧字段：

- `dependency_signals`
- 正式 schema 里的 `raw_signals`

当前 `context` 已切到更柔性的表达：

- `clarify_hint`
- `ambiguity_states`
- `missing_context_types`
- `needs_previous_answer`

这意味着 `evidence` 不再把“是否必须澄清”当成唯一强结论，而是更偏：

- 上下文事实
- 理解缺口
- 模糊状态

### 3.2 `resolver` 已基本去执行化

当前 `resolver` 不再把：

- `needs_query_decomposition`
- `needs_agent_planning`

这类执行提示作为主结果直接产出。

任务理解现在主要依赖：

- `complexity`
- `shape`
- `topology`

这让 `compound / complex` 不再只是旧式粗暴吞并，也让“回答结构”和“执行步骤”开始分离。

## 4. 当前最重要的边界

### 4.1 rule 层还保留什么

当前 rule 层应该保留：

- `unsupported / safety`
- `qa / chat / system / unsupported` 粗分类
- `follow_up / ask_source / challenge / soft_doubt` 粗识别
- baseline / teacher / regression anchor

### 4.2 rule 层不该继续强扛什么

当前不建议继续往 rule 层压这些职责：

- 强 clarify 裁决
- 细粒度 task 终判
- 回答结构 vs 执行步骤终判
- 柔性 decomposition
- 过细 workflow 决策

### 4.3 evidence/resolver 和 control/workflow 的边界

当前建议始终坚持：

- `evidence + resolver` 负责 understanding
- `control` 负责粗分流
- `workflow` 负责真正执行

也就是说：

- understanding 可以 `workflow-aware`
- 但不应该 `workflow-deciding`

## 5. 当前最值得记住的正式语义

### 5.1 understanding 主骨架

- `intent`
- `task`
- `context`
- `safety`

### 5.2 task 关键轴

- `complexity`
- `shape`
- `topology`

其中 `topology` 的意义是：

- `single`
- `parallel_queries`
- `parallel_subtasks`
- `staged`

它描述的是任务结构，而不是直接承诺后续必须如何执行。

### 5.3 context 关键表达

当前更重要的不是旧式 `needs_clarification`，而是：

- `clarify_hint`
- `ambiguity_states`
- `missing_context_types`

它们回答的是：

- 是否可能需要澄清
- 当前为什么模糊
- 缺的到底是哪类上下文信息

## 6. 当前仍未完成的部分

这条线当前最明显的未完成项不是 `evidence/resolver`，而是：

1. `control v2` 后续迁移
- 最小结构已落地
- 但旧兼容字段尚未完全退出
- workflow 侧还没有全面转向消费新结构

2. `workflow` 边界落地
- 还没有把新的 understanding 语义完整接到执行流里

3. model-centric understanding 的真正放量
- 当前模型证据接口已经有挂点
- 但整体仍是 rule-first baseline

## 7. 当前应如何阅读其它文档

如果你当前要继续推进：

- `evidence / resolver`
  - 先看 [signal_info/README.md](/C:/Users/HUAWEI/PycharmProjects/Skill-First-Hybrid-RAG/notes/intent/signal_info/README.md)

- `评估 / 训练准备 / baseline`
  - 先看 [intent_testing_and_evaluation.md](/C:/Users/HUAWEI/PycharmProjects/Skill-First-Hybrid-RAG/notes/intent/intent_testing_and_evaluation.md)

- `rule confidence`
  - 先看 [intent_rule_confidence.md](/C:/Users/HUAWEI/PycharmProjects/Skill-First-Hybrid-RAG/notes/intent/intent_rule_confidence.md)

- `老的多信号 backfill 计划`
  - 只当历史参考读 [multisignal_dev_heldout_backfill_plan_20260517.md](/C:/Users/HUAWEI/PycharmProjects/Skill-First-Hybrid-RAG/notes/intent/multisignal_dev_heldout_backfill_plan_20260517.md)
