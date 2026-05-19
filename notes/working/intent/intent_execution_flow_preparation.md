# Intent Execution Flow Preparation

这份文档面向这样一个假设前提：

> `intent` 小模型 SFT 已经完成第一版，接下来不再主要讨论“怎么训”，而是讨论“怎么把它安全接进现有执行流”。

它的用途不是替代架构文档，而是给并行协作提供一个统一准备面：

- 哪些事情现在可以并行做
- 哪些边界先不要碰
- 执行流接入时的真实落点在哪里
- 第一版集成的验收口径是什么

当前放在 `notes/working/intent/`，因为这仍然是阶段性执行准备文档，不是最终稳定制度。

---

## 1. 当前阶段目标

当前阶段的核心目标，不是再扩 SFT 数据，而是把已经具备初步能力的小模型接入现有链路，验证它是否能在**不破坏规则可解释性和粗分流稳定性**的前提下，提升 evidence 层识别质量。

一句话说：

> 从“模型训练完成”切到“模型进入真实执行流，但仍受规则与现有 control 约束”的阶段。

当前默认目标：

1. 先接 evidence 层，不直接替换 resolver / control
2. 先做增强，不做全量重写
3. 先可观测，再追求收益最大化

---

## 2. 当前执行流边界

根据现有 intent 设计，执行流主线仍然是：

```text
input
  -> evidence
  -> resolved
  -> control
  -> 后续执行流
```

其中边界必须先冻结：

### 2.1 小模型当前负责什么

第一版小模型只进入 evidence 层，优先承担：

- `soft_doubt`
- `task.shape`
- 后续可能扩展到部分 `required_signals`

它的角色是：

- 补规则层开放表达盲区
- 给 evidence 增加模型侧候选或补充信号
- 为 resolver 提供更稳的上游证据

它**不直接负责**：

- 最终 `main_intent` 定稿
- 最终 `context_dependency` 定稿
- 最终 `control.route / mode` 产出

### 2.2 规则层当前保留什么

第一版仍保留规则层的主导地位，特别是：

- `unsupported`
- `system.capability.ask`
- 高风险安全信号
- 明确 follow-up / missing context 规则
- 已经稳定的 control 映射

换句话说：

> 第一版不是 model-first，而是 rule-first with model evidence augmentation。

### 2.3 resolver / control 当前怎么处理

当前 resolver / control 继续沿用现有逻辑：

- `backend/intent/resolver.py`
- `backend/intent/control_signal.py`

第一版只允许它们“消费更多 evidence”，不允许同时大改其决策哲学。

这样做的原因很明确：

1. 否则很难分清效果提升来自模型，还是来自后层逻辑改写
2. 会把“模型接入验证”变成“整条意图链重构”
3. 不利于并行协作拆任务

---

## 3. 当前真实代码落点

第一版执行流接入，主要会影响以下几个代码区域：

### 3.1 Intent 分类入口

- `backend/intent/classifier.py`

这里是最直接的接入点。第一版建议做法是：

- 保留原规则分类逻辑
- 在 evidence 生成过程中引入模型侧输出
- 把模型输出写入 evidence，可被后续 resolver 消费

### 3.2 Resolver 收敛

- `backend/intent/resolver.py`

这里第一版只做最小改动：

- 接收新的 evidence 字段
- 明确哪些模型证据可参与收敛
- 明确规则优先级不被意外打穿

### 3.3 Control 映射

- `backend/intent/control_signal.py`

这里不应直接做“大模型化”或“重做分流策略”，而是只验证：

- 新 evidence 是否让现有 resolved 更稳
- 是否减少误进错误执行流

### 3.4 Agent 执行流主入口

- `backend/graph/agent.py`
- `backend/api/chat.py`

这一层的重点不是理解 query，而是：

- 接住新的意图结果
- 保持 retrieval / answer / tool flow 正常
- 提供观察点，能看出模型接入前后有什么变化

---

## 4. 并行工作建议

为了支持你并行推进，建议把工作拆成 5 条并行线，每条线都尽量边界清晰。

### 4.1 线 A：模型产物接入线

目标：

- 定义小模型推理产物如何进入 classifier
- 明确输入输出接口

主要内容：

- 模型推理输入格式
- 模型输出字段映射
- evidence 写入位置
- 空结果 / 低置信 / 推理失败时的回退逻辑

交付物：

- 模型 inference adapter
- evidence 接入约定

### 4.2 线 B：evidence 合并策略线

目标：

- 定义规则 evidence 和模型 evidence 如何共存

主要内容：

- 哪些字段可直接补充
- 哪些字段只能做 candidate，不可直接盖掉规则
- 冲突时谁优先
- 哪些信号必须 rule hard gate

交付物：

- evidence merge policy
- 冲突样例表

### 4.3 线 C：resolver / control 稳定性线

目标：

- 确保模型接入后不会把下游粗分流打乱

主要内容：

- 评估 resolved 是否更稳
- 评估 route / mode 是否发生异常漂移
- 确认哪些 drift 可接受，哪些不可接受

交付物：

- 集成前后 diff 报告
- route / mode 风险清单

### 4.4 线 D：评估与回归线

目标：

- 为模型接入建立独立于训练阶段的执行流评估口径

主要内容：

- layer-level eval
- end-to-end eval
- batch 级错误分析
- 规则版 vs 模型增强版 对照

交付物：

- evidence 对比评估
- resolved / control 回归评估
- 执行流级 badcase 列表

### 4.5 线 E：观测与开关线

目标：

- 确保接入后可灰度、可关闭、可追踪

主要内容：

- 是否启用模型 evidence 开关
- trace 中如何记录模型参与
- 如何区分规则命中、模型补充、最终收敛来源

交付物：

- feature flag
- trace / log 字段定义
- 失败回退方案

---

## 5. 第一版接口与输出约定

为了让并行同学不各写一套，第一版先统一这几个约定。

### 5.1 输入侧

模型推理的输入仍然来自 intent `input`：

- `user_query`
- 必要时的 `history`
- 可选结构化上下文

第一版不建议在执行流阶段再做另一套 query 改写后输入模型，否则会让训练口径和线上口径分叉太大。

### 5.2 输出侧

模型输出第一版建议只产出 evidence 相关结果，例如：

- `soft_doubt` 预测
- `task_shape` 预测
- 可选置信度
- 可选 top-k candidates

第一版不建议直接让模型输出完整：

- `main_intent`
- `route`
- `mode`

因为这会和现有 resolver / control 责任重叠。

### 5.3 落入 evidence 的方式

第一版建议把模型结果作为 evidence 中的显式子来源保留，至少保证：

- 能区分 rule evidence 和 model evidence
- 能看到最终 resolved 用没用到模型输出
- 能在评估脚本里单独分析模型接入贡献

推荐心智模型：

```text
rule evidence
+ model evidence
-> merged evidence
-> resolver
-> control
```

---

## 6. 第一版验收标准

第一版不是“模型只要接上就算成功”，而是要同时满足三类标准。

### 6.1 Evidence 层收益

至少要看到以下之一：

- `soft_doubt` 漏召回下降
- `task.shape` 边界更稳
- 开放表达下 evidence 更少缺关键信号

### 6.2 下游稳定性

不能出现明显副作用：

- `resolved.main_intent` 大面积漂移
- `control.route` 误分流明显增加
- `system / unsupported` 被误吸入普通 QA

### 6.3 工程可控性

必须具备：

- 模型开关
- 失败回退
- trace 可见
- 回归评估入口

如果这四项没有，就算局部指标变好，也不适合并入主执行流。

---

## 7. 当前推荐推进顺序

第一版建议按下面顺序推进，而不是并行乱入。

### 阶段 1：接入准备

- 冻结第一版模型任务范围
- 冻结 evidence merge 规则
- 确认 trace 与开关方案

### 阶段 2：离线集成验证

- 在评估集上跑 rule-only vs rule+model
- 看 evidence / resolved / control 三层差异
- 不先接真实 chat 主链

### 阶段 3：执行流灰度接入

- 接进 `classifier -> resolver -> control`
- 先保留可关闭开关
- 只做小范围 internal 验证

### 阶段 4：执行流回归

- 跑 intent 评估
- 跑 chat 主链回归
- 重点看 route drift、引用要求、follow-up 稳定性

### 阶段 5：整理稳定结论

- 如果第一版接入稳定，再把 working 结论提炼到稳定文档

---

## 8. 当前风险清单

第一版最值得提前防的，不是模型效果差，而是接入方式不干净。

### 风险 1：模型与规则职责重叠

表现：

- evidence、resolved、control 三层都在吃模型输出
- 最后无法解释错误来自哪一层

应对：

- 第一版只让模型先进入 evidence

### 风险 2：线上口径和训练口径分叉

表现：

- 训练时看的是一套输入
- 线上又做了另一套改写或额外拼接

应对：

- 第一版尽量保持训练输入和线上推理输入同构

### 风险 3：提升 evidence，破坏 control

表现：

- 某些边界分类更“聪明”了
- 但实际把请求送进了更差的执行流

应对：

- 必须把 `control.route / mode` 回归评估列为硬验收项

### 风险 4：并行开发各自定义接口

表现：

- inference adapter 一套格式
- resolver 消费另一套格式
- 评估脚本看第三套字段

应对：

- 先冻结 model evidence 的最小接口，再开工

---

## 9. 当前结论

如果现在把“小模型 SFT 已完成”视为既成事实，那么接下来的正确动作不是马上重写整条意图链，而是：

> 以 evidence 层为唯一第一落点，把模型作为规则增强器接进现有 `input -> evidence -> resolved -> control` 链路，并用可回退、可观测、可回归的方式验证它是否真的改善了执行流前半段。

并行协作时，最重要的不是“大家都开始改代码”，而是先共享这三条共识：

1. 第一版只接 evidence，不重做 resolver / control  
2. 第一版先保证可观测与可回退，再追求收益最大化  
3. 第一版成功标准是“evidence 改善 + 下游稳定”，而不是单看某个分类头分数更高

