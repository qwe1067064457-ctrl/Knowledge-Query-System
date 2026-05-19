# Intent 信号说明

## 1. 当前目录的定位

这个目录专门沉淀 `evidence` 层的正式信号体系。

当前 `V2` 口径下，只保留一套正式语义分类：

- `intent`
- `task`
- `context`
- `safety`

这份目录的目标不是再造第二套抽象，而是回答：

- 某个信号属于哪一类
- 哪些字段是 resolver 的主输入
- 哪些旧字段已经退出正式 schema
- 当前 `evidence v2` 到底怎么读

## 2. 当前正式结构

当前 `evidence` 最重要的正式结构是：

- `candidate_intents`
- `task_candidates`
- `context_signals`
- `unsupported_signals`

它们分别对应：

- `intent`
- `task`
- `context`
- `safety`

另外仍会有辅助字段：

- `matched_rules`
- `signal_buckets`
- `rule_confidence`
- `model_result`

但这些不构成第二套正式语义分类。

## 3. 当前每一类最关心什么

### `intent`

关注：

- 用户想干什么

主要通过：

- `candidate_intents`

### `task`

关注：

- 任务是什么结构
- 复杂度如何

主要通过：

- `task_candidates`

### `context`

关注：

- 当前依赖哪些上下文事实
- 当前缺哪些理解信息

主要通过：

- `context_signals`

当前重点字段包括：

- `clarify_hint`
- `ambiguity_states`
- `missing_context_types`
- `needs_previous_answer`

### `safety`

关注：

- 是否越界
- 是否需要硬拦截

主要通过：

- `unsupported_signals`

## 4. 当前已经退出正式 schema 的旧字段

下面这些不再属于正式 `evidence v2` 主结构：

- `dependency_signals`
- 正式 schema 里的 `raw_signals`

它们如果还出现在历史文档、旧样本、迁移脚本讨论中，应理解为：

- 旧语义遗留
- 历史参考
- 迁移过渡材料

而不是当前 source of truth。

## 5. 当前最重要的阅读入口

### [evidence_signal_info/README.md](/C:/Users/HUAWEI/PycharmProjects/Skill-First-Hybrid-RAG/notes/intent/signal_info/evidence_signal_info/README.md)

适合：

- 想看 `evidence v2` 的正式读取方式
- 想知道哪些旧解释已经失效

## 6. 这份目录现在不再主推什么

当前不再推荐把 `evidence` 理解成：

- 规则命中层
- 业务信号层
- 解释约束层
- 候选结果层

这套说法可以帮助理解历史实现，但不再是当前文档的正式主轴。

当前唯一正式主轴就是：

- `intent`
- `task`
- `context`
- `safety`
