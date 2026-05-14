# Intent Notes README

## 信号说明入口

细粒度信号说明放在：

- [signal_info](./signal_info/README.md)
- [evidence_signal_info](./signal_info/evidence_signal_info/README.md)

其中 `evidence_signal_info` 重点说明：

- `matched_rules`
- `signal_buckets`
- `dependency_signals`
- `ContextSignals`
- `unsupported_signals`
- `candidate_intents`
- `task_candidates`
- `rule_confidence`

这组文档用于回答：

```text
某个 evidence 字段属于哪一层？
它是规则命中、业务信号、解释约束，还是候选结果？
哪些信号容易混淆？
CandidateIntent.score 和 rule_confidence 有什么区别？
```

## 1. 目录目标

`notes/intent` 用来沉淀当前 `intent` 模块的：

- 架构说明
- 规则与 confidence 设计
- 测试与评估口径
- 规则调优记录
- 后续 TODO 和迁移方向

如果后面继续做规则层优化、小模型接入、动态规则维护，这个目录就是主入口。

---

## 2. 文档索引

### [intent_project_info.md](/C:/Users/HUAWEI/.codex/worktrees/2a18/Skill-First-Hybrid-RAG/notes/intent/intent_project_info.md)

适合看什么：

- `input -> evidence -> resolved -> control` 四层结构
- evidence / resolved / control 的字段分类
- `global stable rules` 与 `group_shared / domain bootstrap rules` 的分层
- 当前实现范围
- 当前长期 TODO

一句话：

- 这是 `intent` 模块的总览文档

### [intent_rule_confidence.md](/C:/Users/HUAWEI/.codex/worktrees/2a18/Skill-First-Hybrid-RAG/notes/intent/intent_rule_confidence.md)

适合看什么：

- 规则版 `confidence` 是什么
- 它为什么不是统计概率
- base / support bonus / conflict / context adjustment 是怎么工作的

一句话：

- 这是“规则强度解释器”的说明文档

### [intent_testing_and_evaluation.md](/C:/Users/HUAWEI/.codex/worktrees/2a18/Skill-First-Hybrid-RAG/notes/intent/intent_testing_and_evaluation.md)

适合看什么：

- 单元测试覆盖了什么
- `overall / per_batch / rule_stats` 怎么理解
- 当前评估是端到端口径，不是全面的 layer-isolated eval
- 数据集四层标注结构

一句话：

- 这是测试与评估口径文档

### [rule_tuning.md](/C:/Users/HUAWEI/.codex/worktrees/2a18/Skill-First-Hybrid-RAG/notes/intent/rule_tuning.md)

适合看什么：

- 每轮规则优化改了什么
- 当前瓶颈是什么
- 哪些规则已可严格评估，哪些还只是部分可评估
- 下一步还值得继续调什么

一句话：

- 这是规则维护和调优日志

### [rule_supervision.md](/C:/Users/HUAWEI/.codex/worktrees/2a18/Skill-First-Hybrid-RAG/notes/intent/rule_supervision.md)

适合看什么：

- 为什么有些规则目前只有 `hits`
- 规则级监督该怎么补
- 哪些规则优先补
- 人工参与需要裁决什么

一句话：

- 这是规则级监督和标注口径说明文档

### [sft_preparation.md](/C:/Users/HUAWEI/.codex/worktrees/2a18/Skill-First-Hybrid-RAG/notes/intent/sft_preparation.md)

适合看什么：

- 训练集导出字段
- `gold / silver / weak` 分层
- 冻结 held-out 的使用方式
- 第一版小模型的任务边界

一句话：

- 这是 intent 小模型训练准备文档

---

## 3. 推荐阅读顺序

如果你第一次接手 `intent` 模块，建议按下面顺序看：

1. [intent_project_info.md](/C:/Users/HUAWEI/.codex/worktrees/2a18/Skill-First-Hybrid-RAG/notes/intent/intent_project_info.md)
2. [intent_testing_and_evaluation.md](/C:/Users/HUAWEI/.codex/worktrees/2a18/Skill-First-Hybrid-RAG/notes/intent/intent_testing_and_evaluation.md)
3. [rule_tuning.md](/C:/Users/HUAWEI/.codex/worktrees/2a18/Skill-First-Hybrid-RAG/notes/intent/rule_tuning.md)
4. [rule_supervision.md](/C:/Users/HUAWEI/.codex/worktrees/2a18/Skill-First-Hybrid-RAG/notes/intent/rule_supervision.md)
5. [intent_rule_confidence.md](/C:/Users/HUAWEI/.codex/worktrees/2a18/Skill-First-Hybrid-RAG/notes/intent/intent_rule_confidence.md)
6. [sft_preparation.md](/C:/Users/HUAWEI/.codex/worktrees/2a18/Skill-First-Hybrid-RAG/notes/intent/sft_preparation.md)

原因：

- 先理解结构
- 再理解评估口径
- 再看当前问题和调优历史
- 最后再看 `confidence` 细节

---

## 4. 当前重点

当前 `intent` 模块已经明确了几件事：

- `control` 层相对清楚，主要负责执行流映射
- `resolved` 层主要做收敛，不负责补全缺失语义
- `evidence` 层是当前主要瓶颈
- 规则层已经不再追求覆盖所有开放表达，而是转向：
  - 稳定
  - 可迁移
  - 可供训练

当前规则资产也已经分层：

- `global stable rules`
- `group_shared / domain bootstrap rules`

其中 `domain bootstrap` 这层已经开始配置化外提，后续动态调优 agent 应优先修改配置资产，而不是直接改主分类逻辑。

---

## 5. 当前 TODO 入口

如果要继续推进，优先去看：

- [intent_project_info.md](/C:/Users/HUAWEI/.codex/worktrees/2a18/Skill-First-Hybrid-RAG/notes/intent/intent_project_info.md)
  - 看长期 TODO 和架构方向
- [rule_tuning.md](/C:/Users/HUAWEI/.codex/worktrees/2a18/Skill-First-Hybrid-RAG/notes/intent/rule_tuning.md)
  - 看规则层还值得做什么
- [intent_testing_and_evaluation.md](/C:/Users/HUAWEI/.codex/worktrees/2a18/Skill-First-Hybrid-RAG/notes/intent/intent_testing_and_evaluation.md)
  - 看当前评估口径和数据边界

---

## 6. 一句话总结

这个目录记录的是：

> `intent` 模块如何从“规则分类器”演化成“有结构、有评估、有调优记录、可接小模型和动态规则维护”的意图识别系统。
