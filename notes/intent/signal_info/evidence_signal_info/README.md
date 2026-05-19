# Evidence 信号说明

## 1. 当前文档作用

这份文档只解释当前 `evidence v2` 如何阅读。

核心结论很简单：

- 当前 `evidence` 的正式分类只有一套
- 就是：
  - `intent`
  - `task`
  - `context`
  - `safety`

不要再把旧的多层术语当作正式结构。

## 2. 当前主骨架

从 resolver 的主消费角度看，当前 `evidence` 主骨架是：

- `candidate_intents`
- `task_candidates`
- `context_signals`
- `unsupported_signals`

对应关系：

- `candidate_intents` -> `intent`
- `task_candidates` -> `task`
- `context_signals` -> `context`
- `unsupported_signals` -> `safety`

## 3. 当前辅助字段

除主骨架外，当前仍有少量辅助字段：

- `matched_rules`
- `signal_buckets`
- `rule_confidence`
- `model_result`

它们的作用分别是：

- `matched_rules`
  - 规则来源证据
- `signal_buckets`
  - 四大类信号总览
- `rule_confidence`
  - 规则证据可信度评审
- `model_result`
  - 可选的模型补充证据接口

这些字段重要，但它们不是第二套正式语义分类。

## 4. 当前 `signal_buckets` 怎么看

`signal_buckets` 仍然有用，但它的定位是：

- 四大语义类下的信号总览

当前只应按下面四类理解：

- `intent`
- `task`
- `context`
- `safety`

它不是“比 typed fields 更正式”的主结构，而是：

- 比 `matched_rules` 更高层
- 比 `candidate/context/safety typed fields` 更概览

## 5. 当前 `context` 怎么看

当前 `context` 的主表达已经从旧的强裁决信号，转向更柔性的缺口表达。

重点看：

- `clarify_hint`
- `ambiguity_states`
- `missing_context_types`
- `needs_previous_answer`

它们回答的是：

- 是否可能需要澄清
- 当前哪里模糊
- 当前具体缺什么信息
- 是否缺上一轮回答这个事实依托

这比旧式 `needs_clarification` 更贴合当前 `V2` 目标。

## 6. 当前不再作为正式主结构的字段

### `dependency_signals`

已退出正式 `evidence v2` schema。

原因：

- 它和 `ContextSignals` 重复
- 它属于旧兼容表达
- 继续保留只会让 `context` 再次变乱

### `raw_signals`

也已退出正式 schema。

原因：

- 它对调试有价值
- 但不适合作为正式训练或 resolver 主消费结构

## 7. 当前这份目录与子文档的关系

本目录下其余文档里，仍可能出现旧术语，例如：

- `dependency_signals`
- 规则命中层 / 业务信号层 / 解释约束层 / 候选结果层

这些内容可作为历史理解参考，但如果与本 README 冲突：

- 以本 README 和上级 [signal_info/README.md](/C:/Users/HUAWEI/PycharmProjects/Skill-First-Hybrid-RAG/notes/intent/signal_info/README.md) 为准
