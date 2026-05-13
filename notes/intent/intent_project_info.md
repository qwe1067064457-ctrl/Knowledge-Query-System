# Intent 模块项目说明

## 一、模块定位

`Intent` 模块的目标不是直接回答问题，也不是提前决定所有执行细节。

它的职责是：

- 识别当前用户输入属于哪一类请求
- 判断它是否依赖上下文
- 判断它是简单任务、复合任务还是复杂任务
- 产出稳定的 `resolved intent`
- 进一步映射成粗粒度 `control signal`

当前我们已经明确：

> 意图识别层负责把方向定稳，把明显模式标出来，把危险输入拦住；真正的执行优化仍在后续执行流中完成。

这层重点解决：

- 不让复杂问题掉进简单执行流
- 不让简单问题误进复杂执行流
- 不让危险或越权输入混入普通知识问答流

---

## 二、当前架构

当前 Intent 识别采用四层结构：

```json
{
  "input": {},
  "evidence": {},
  "resolved": {},
  "control": {}
}
```

### 1. `input`

表示进入意图识别模块的输入。

当前包括：

- `user_query`
- `context_state`
- `model_context`

其中：

- `context_state` 给规则层使用
- `model_context` 给模型层使用

规则层不直接拼接完整历史文本做正则，而是尽量依赖结构化上下文状态。

### 2. `evidence`

表示规则和模型识别出的多值证据。

这一层允许：

- 多值
- 冲突
- 解释性字段

当前主要包括：

- `classifier_mode`
- `matched_rules`
- `raw_signals`
- `signal_buckets`
- `unsupported_signals`
- `dependency_signals`
- `candidate_intents`
- `task_candidates`
- `model_result`

后续更推荐按子域理解它：

- `intent_evidence`
- `task_evidence`
- `context_evidence`
- `safety_evidence`

只是当前代码还没有把 `evidence` 物理拆成四个子对象，而是逻辑上已经这样划分。

从当前实现开始，我们额外提供两种阅读方式：

- `to_dict()`
  - 保持兼容的扁平结构，方便旧测试、旧评估脚本继续使用
- `to_grouped_dict()`
  - 提供按 `meta / intent / task / context / safety` 分组后的结构，方便调试和后续重构

并且从这一版开始，规则层已经优先产出 `signal_buckets`：

- `signal_buckets.intent`
- `signal_buckets.task`
- `signal_buckets.context`
- `signal_buckets.safety`

`raw_signals` 仍然保留，但角色已经下沉为：

- 兼容旧测试 / 旧评估脚本
- 给 `rule_confidence` 这类仍按扁平信号集工作的模块使用
- 作为调试日志的“拍平视图”

#### 2.1 `evidence` 的子域分类（推荐心智模型）

这套分类的目的，是让我们在评估/调优时能明确“薄弱点到底在意图、任务、上下文还是安全拦截”，避免把所有问题都混在 `raw_signals` 里。

- `intent_evidence`：回答“它大概是什么意图？”
  - 典型字段：`candidate_intents`、`raw_signals`（`qa/chat/system/...` 相关）、部分 `matched_rules`
  - 典型规则：`intent.*`、`system.*`、`challenge.*`、`source.*`
- `task_evidence`：回答“它要做什么形状/复杂度的任务？”
  - 典型字段：`task_candidates`、部分 `raw_signals`（`multi_question/complex`）、部分 `matched_rules`
  - 典型规则：`task.*`
- `context_evidence`：回答“它是否依赖上文？依赖哪种上文？”
  - 典型字段：`dependency_signals`、与上下文相关的 `matched_rules`、部分 `raw_signals`（如 `follow_up`）
  - 典型规则：`context.*`、`source.missing_context`、`challenge.missing_context`
- `safety_evidence`：回答“是否越权/不支持/需要拒绝或拦截？”
  - 典型字段：`unsupported_signals`、部分 `raw_signals`（`unsupported/out_of_scope`）、相关 `matched_rules`
  - 典型规则：`unsupported.*`

### 3. `resolved`

表示 resolver 收敛后的稳定结果。

这是执行流真正依赖的结构化意图结果。

当前包括：

- `main_intent`
- `modifiers`
- `task`
- `context_dependency`
- `decision`

其中：

- `main_intent` 单值
- `modifiers` 多布尔并存
- `task.complexity` 单值
- `task.shape` 单值
- `context_dependency` 单值

#### 3.1 `resolved` 的分类（Intent / Task / Context / Decision）

`resolved` 虽然是一个对象，但在调试和评估时建议按以下四块拆开看（对应我们常说的 intent/task/context 三维，再加上决策解释）：

- `intent`
  - `main_intent`（单值）
  - `modifiers`（多布尔并存）
- `task`
  - `task.complexity`（单值）
  - `task.shape`（单值）
- `context`
  - `context_dependency`（单值）
- `decision`
  - `decision.strength/source/reason`（用于可解释性、回归对比、灰度分析）

同样地，`resolved` 现在也同时支持：

- `to_dict()`
  - 保持现有扁平结构
- `to_grouped_dict()`
  - 按 `intent / task / context / decision` 输出

### 4. `control`

表示给执行流使用的粗分流信号。

当前包括：

- `route`
- `mode`
- `rewrite`
- `force_citation`
- `use_planner`
- `decompose_query`

当前原则是：

> `control` 只做粗分流，不提前决定所有执行细节。

为降低阅读成本，`control` 现在建议按两块理解：

- `dispatch`
  - `route`
  - `mode`
- `policy`
  - `rewrite`
  - `force_citation`
  - `use_planner`
  - `decompose_query`
  - `planning_level`

---

## 三、主意图与任务定义

## 3.1 `main_intent`

当前确定为：

- `qa`
- `chat`
- `system`
- `unsupported`

含义：

- `qa`
  - 基于知识库的知识问答、解释、对比、总结、验证
- `chat`
  - 普通闲聊
- `system`
  - 问系统能力、功能、用法、范围
- `unsupported`
  - 当前普通用户入口不支持的操作

注意：

- “知识库里最后没查到答案”不是一个新的 intent
- 它仍然是 `qa`
- “没检索到”属于执行流检索后的 fallback，而不是意图识别阶段决定的类别

## 3.2 `modifiers`

当前保留：

- `follow_up`
- `challenge`
- `ask_source`
- `ask_capability`
- `needs_clarification`
- `out_of_scope`

说明：

- modifier 允许多值并存
- 例如 `challenge + ask_source`
- 例如 `follow_up + complex`

## 3.3 `task.complexity`

当前定义：

- `simple`
- `compound`
- `complex`

含义：

- `simple`
  - 单问题，普通 RAG 可处理
- `compound`
  - 一句话多个问题，但问题相对独立
- `complex`
  - 需要规划、比较、验证、归纳、整理、综合

我们已经明确：

```text
simple < compound < complex
```

这不是语义价值排序，而是执行需求偏序。

目的：

- 避免复杂任务误落到简单流

## 3.4 `task.shape`

当前定义：

- `single_question`
- `multi_question`
- `compare`
- `summarize`
- `extract`
- `verify`
- `mixed`
- `none`

原则：

- evidence 层允许多个候选 shape
- resolved 层必须收敛成单值
- 无法自然合并时，收敛为 `mixed`

---

## 四、规则层与模型层

## 4.1 规则层作用

规则层不是要独立完成全部意图识别，而是：

- 识别高确定性模式
- 生成 evidence
- 决定后续识别模式

当前已经明确三类模式：

- `rule_only`
- `rule_plus_model`
- `model_first_with_rule_guard`

## 4.2 三类模式

### 1. `rule_only`

高强度规则足够判定，不需要模型主判。

适合：

- `ask_capability`
- `unsupported`
- 明确 `challenge`

### 2. `rule_plus_model`

规则和模型共同产出 evidence，再由 resolver 收敛。

适合：

- 模糊 `qa/chat`
- 隐含 `follow_up`
- 复杂任务
- 多形态任务

### 3. `model_first_with_rule_guard`

模型主判，规则只做：

- schema guard
- safety guard
- unsupported 拦截

适合：

- 规则很难判断的复杂 query
- 高语义、多层含义输入

注意：

- 这三类模式都是由规则层触发
- 不是让模型自己决定模式

## 4.3 当前模型层实现

当前没有做 SFT。

先做的是：

- 大模型结构化分类
- 严格 JSON schema 输出
- 规则兜底

相关 prompt 位于：

- [intent_classifier_prompt.md](/C:/Users/HUAWEI/PycharmProjects/Skill-First-Hybrid-RAG/backend/prompts/intent_classifier_prompt.md)

模型层当前只输出：

- `candidate_intents`
- `modifiers`
- `task_candidates`
- `context_dependency`
- `confidence`
- `reason`

模型不直接输出 `control`。

---

## 五、resolver 设计

resolver 的作用是：

- 把多值 evidence 收敛成稳定单值
- 让执行流容易实现
- 保留 modifier 多值，不把一切压成单标签

当前我们已经明确：

- `main_intent` 单值
- `task.complexity` 单值
- `task.shape` 单值
- `context_dependency` 单值
- `modifiers` 多值保留

### 为什么必须收敛

因为 evidence 层允许同时出现：

- `qa`
- `challenge`
- `ask_source`
- `multi_question`

如果这些直接驱动执行流，会导致执行流判断混乱。

因此必须有：

- 一个主路线
- 一组 modifier
- 一个任务复杂度
- 一个任务形态

### 当前 resolver 优先级

当前建议：

```text
unsupported
> system
> challenge
> complex qa
> compound qa
> simple qa
> chat
```

说明：

- `ask_source`、`follow_up` 不作为主路线
- 它们以 modifier 形式保留

---

## 六、control signal 设计

当前 `control` 只做粗分流。
(tag:为什么没有对task.shape=mixed的体现, 目前我看到的只有针对task和intent这两个参数的转化,其余参数没有)
当前主要字段：

- `route`
- `mode`
- `rewrite`
- `force_citation`
- `use_planner`
- `decompose_query`
- `planning_level`

当前分流规则大意如下：

- `simple qa -> rag`
- `compound + multi_question -> rag + decompose_query`
- `complex -> agent + planning_level`
- `challenge -> rag + challenge`
- `system -> direct + capability`
- `unsupported -> reject`
- `needs_clarification -> direct + clarify`

注意：

- 这层只回答“走哪条主路”和“用什么执行模式”
- 它不应该承担过多解释职责

### 6.1 `control` 为什么不完整映射所有 `resolved` 字段

当前 `control` 是粗分流层，不是执行计划本身。

它的职责是：

- 决定是否进入 `rag / chat / direct / agent / reject`
- 决定是否启用少量高价值执行开关

它不负责：

- 保留 `resolved` 层的全部语义细节
- 把每个 `task.shape` 都映射成独立执行协议

因此会出现一种正常现象：

- `resolved.task.shape` 语义比 `control` 更丰富
- `control` 只消费那些已经有稳定执行含义的字段

例如：

- `multi_question -> decompose_query`
- `challenge -> mode=challenge`
- `complex -> route=agent`

而像 `mixed` 这样的 shape，当前不会直接变成单独 route，而是作为：

- 复杂任务的重要语义标签
- planner 分级策略的输入之一

### 6.2 为什么 `task.shape=mixed` 没有单独映射

`mixed` 表示：

- 当前 query 的任务形态无法自然压成单一 `compare / summarize / extract / verify`
- 它通常意味着多动作混合，而不是某一种标准执行模板

因此 `mixed` 本身不直接回答：

- 是否必须拆 query
- 是否必须显式 planner
- 是否可以普通 RAG 直接回答

当前策略是：

- `mixed` 先保留在 `resolved` 中，确保语义不丢
- 当 `complexity=complex` 且 `shape=mixed` 时，倾向走 `agent`
- 由 `planning_level` 再决定是 `full` 还是更轻量的规划

换句话说：

- `mixed` 不消失
- 它只是暂时不直接映射成独立 route，而是参与 planner 决策

### 6.3 `direct` 是什么执行流

`direct` 不是回答内容，而是执行路径类型。

它表示：

- 不进入知识检索主链路
- 不进入复杂 agent 执行链路
- 由系统直接返回一个结构化响应

当前主要有两种 `direct` 子模式：

- `direct + capability`
  - 用于系统能力、功能、范围、使用方式问题
  - 默认不依赖知识库检索
- `direct + clarify`
  - 用于输入不充分、指代不清、缺少前提的问题
  - 默认先补信息，再决定是否进入检索

### 6.4 为什么 `needs_clarification` 默认不先走 RAG

`needs_clarification` 的核心问题通常不是“缺证据”，而是“缺前提”：

- 指代对象不清
- 用户问题不完整
- 缺关键事实
- 缺上下文锚点

在这种情况下直接检索，风险通常比收益更大：

- 容易检索错方向
- 容易把错误前提带进回答
- 容易生成看似有依据、其实答偏的内容

因此当前默认策略是：

- `route=direct`
- `mode=clarify`

这不等于“永远不需要证据”，而是：

> 在证据检索前，先补齐检索前提。

后续如果要增强，也可以考虑：

- `clarify_soft`
  - 允许轻量检索辅助生成澄清问题
- `clarify_hard`
  - 完全不检索，直接追问

但第一版默认应优先保守。

### 6.5 复杂任务是否都适合 planner

不是所有 `complex` 都必须绑定同一强度的 planner。

当前更合理的方向是分级：

- `planning_level=full`
  - 适合 `complex + compare`
  - 适合 `complex + mixed`
  - 原因是多主体、多动作任务最容易漏项
- `planning_level=light`
  - 适合 `complex + verify`
  - 适合 `complex + extract`
  - 需要先组织步骤，但不一定值得显式生成独立 plan
- `planning_level=none`
  - 适合 `complex + summarize`
  - 适合路径固定、总结目标明确的复杂任务

因此当前建议把 `use_planner` 理解为：

- 是否启用显式 planner

而不是：

- 是否需要任何形式的规划思考

---

## 七、当前实现范围

当前已经落地：

- 四层结构核心对象
- 规则 evidence 生成
- resolver 收敛
- control signal 映射
- `agent.py` 已接入新 intent 流水线
- 模型分类器占位和 prompt 文件
- 规则评估脚本与种子数据

当前还没有继续做的内容：

- challenge claim 抽取
- challenge 检索 query 构造
- agent/planner 细粒度执行优化
- 小模型 SFT
- 真实大规模规则质量验证后的系统性调参

原因是：

- 这些已经超出“意图识别第一版”的范围
- 当前优先目标是把意图识别结构、粗分流和评估体系稳定下来

---

## 八、后续重点

当前最重要的后续方向，不是继续扩执行流，而是：

### 1. 做真实数据评估

不是只看合成样本，而是收集真实 query：

- `simple_qa`
- `follow_up`
- `challenge`
- `ask_source`
- `system`
- `unsupported`
- `compound_multi_question`
- `complex_task`
- `ambiguous`

### 2. 逐条规则验证

每条规则都需要看：

- 覆盖率
- 命中表现
- 冲突情况

### 3. 决定是否真的需要加大模型占比

只有在规则验证之后，才能更清楚地判断：

- 哪些批次规则够用
- 哪些批次必须依赖模型
- 是否值得做小模型或 SFT

---

## 九、一句话总结

当前 Intent 模块已经从“单标签规则判断”升级成：

> 基于 `input -> evidence -> resolved -> control` 四层结构的可解释意图识别与粗分流模块；它先稳定方向、保留证据、收敛决策，再把请求送入后续执行流。
