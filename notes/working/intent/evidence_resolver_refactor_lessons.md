# Evidence / Resolver 重构经验归档

## 1. 文档定位

这份文档用于归档本轮 `intent` 模块里，围绕 `evidence / resolver` 边界收缩而形成的重构经验。

它回答的不是“某个函数怎么改”，而是这些更上层的问题：

1. 为什么这次必须大改，而不是继续补规则
2. 这次真正暴露出来的架构问题是什么
3. 什么应该继续留在规则层，什么不该再让规则层决定
4. 为什么这轮要走 `V1 冻结 + V2 新开` 的双轨迁移
5. 后续如果继续推进 `workflow`，这里应该保留哪些约束

这份文档放在 `notes/working/intent/`，而不是 `notes/intent/`，因为它仍然属于阶段性重构经验和迁移决策，不是已经冻结的长期制度说明。

---

## 2. 这次为什么必须大改

### 2.1 问题已经不是“规则不够多”

这次最核心的判断是：

> 当前 `intent` 层的主要问题，不再是漏了哪条 regex，而是 `evidence / resolver / control` 的职责边界已经变形。

继续补规则当然还能提高局部命中率，但边际收益已经越来越低，原因不在单点规则，而在整条链路：

```text
input -> evidence -> resolved -> control
```

现在的问题是：

- `evidence` 不只是在收集信号，还在暗含后续执行结论
- `resolver` 不只是在收敛理解结果，还在产出执行提示
- `control` 则继承了上游这些“半理解、半执行”的混合语义

于是最后形成的不是一层“请求理解”，而是一层“过早决定执行”的混合体。

### 2.2 规则层决定了太多本不该提前决定的事

这次讨论里最清晰的一点是：规则层现在承担了至少 5 类不同性质的事情：

1. 基础意图识别
2. 任务复杂度判断
3. 上下文依赖判断
4. 执行流预判
5. 领域冷启动补丁

这些职责混在一起后，几个副作用会同时出现：

- 规则调优难以归因
- `compound / complex` 定义越来越别扭
- “回答结构”和“执行步骤”容易被混淆
- 样本标签越来越依赖当前实现，而不是依赖稳定语义

### 2.3 “先说是否成立，再说依据，再说风险”暴露了边界错误

这类 query 是这次讨论中非常关键的反例。

它看起来像多个步骤，但很多时候本质上只是：

- 一个主题
- 一个回答结构要求
- 一次或少量检索
- 最后交给主模型组织输出

如果在 `resolver` 里过早把它解释成 staged task，就说明系统把：

- `response structuring`

误识别成了：

- `task decomposition`

这正是当前边界模糊的典型信号。

---

## 3. 这次重构真正识别出的结构问题

### 3.1 `evidence` 仍然是主瓶颈

这轮反复确认了一个事实：

> `resolver` 再清楚，也救不了 `evidence` 没抓到的东西。

当前最难的仍然是：

- 开放式表达
- 隐式语义
- meta-style QA
- 边界模糊 query

这意味着后续应该把投入重点继续放在：

- 更好的信号组织
- 更强的上下文表示
- 规则和模型证据如何共存

而不是一味把更多复杂语义硬塞进 `resolver`。

### 3.2 `compound` 和 `complex` 的定义不完整

这次已经明确，当前实现里非常接近：

- `compound == multi_question`
- `complex == compare / summarize / extract / verify / mixed`

并且当两者并存时，`complex` 往往凭裸优先级直接吞掉 `compound`。

这会导致两个问题：

1. 本来只需要多子 query 检索 + 聚合的问题，被过早送进重编排路径
2. `compound` 这个标签越来越像“临时过渡值”，而不是稳定任务语义

所以后续必须把它重新定义成：

- `compound`
  - 多个 sibling query 或并列子任务
  - 不需要规划
  - 更像 `query decomposition`
- `complex`
  - 有步骤依赖、综合比较、核验、抽取、总结
  - 更像 `task decomposition`

### 3.3 `unsupported / clarify / capability` 边界不干净

这轮还暴露出另一个结构问题：

- 缺信息
- 能力边界说明
- 不支持请求

这三件事在当前链路里仍然容易混在一起。

典型信号就是出现了：

- `unsupported -> reject + clarify`

这种语义不干净的映射。

这说明：

- 有些标签是在表达“系统能不能做”
- 有些是在表达“用户信息够不够”
- 有些是在表达“应该如何回复”

但当前规则链路并没有稳定把这三类语义拆开。

### 3.4 `rewrite / decompose` 的原因丢失了

现在系统里很容易只剩：

- `rewrite=True/False`
- `decompose_query=True/False`

但为什么要 rewrite、为什么要 decompose，没有稳定留下来。

这会导致两个后果：

1. 后续执行流只能消费“结果”，很难消费“原因”
2. 样本和评估无法明确区分“触发对了但策略错了”与“根本不该触发”

因此后续需要逐步建立：

- 理解结果
- 执行原因

这两层的分离，而不是继续把一切压成布尔开关。

### 3.5 `ModelContext` 太弱，难以支持高质量绑定

当前上下文信息对这些场景支持都不够强：

- challenge target binding
- ask_source target binding
- clarify slot completion

说明这次重构不只是 task 层的问题，还涉及：

- 上下文表示是否足够结构化
- evidence 层是否有足够输入去判断“这句话到底在追谁”

---

## 4. 这次最重要的重构原则

### 4.1 先删职责，再加能力

这次最重要的经验不是“多定义几个字段”，而是：

> 大改时优先删掉错误职责，再决定哪些能力要重新安放。

具体来说：

- 不要先想怎么把更多能力塞进 `resolver`
- 先想哪些东西根本不该在 `resolver` 里

这也是为什么这次重构方向不是“更多 label”，而是：

- `evidence` 回到信号组织
- `resolver` 回到理解收敛
- `control / workflow` 再去决定执行

### 4.2 回答结构不等于任务分解

这次是一个必须记住的原则：

> 用户要求“分几部分回答”，不等于系统必须“分几步执行”。

很多 query 的真实需求只是：

- 输出结构更清楚
- 论证链更完整

它不一定意味着：

- 需要 planner
- 需要 staged task
- 需要复杂编排

这个原则如果不写进文档，后面很容易再犯同样的错。

### 4.3 能轻量处理的，不要过早送进重路径

这条原则主要对应 `compound`：

- 能通过多次 QA 检索 + 聚合解决的，尽量留在轻路径
- 只有确实存在依赖、比较、综合推理时，再进入复杂路径

这不是性能优化细节，而是系统复杂度控制的核心。

### 4.4 规则层应该是 baseline，不是最终开放语义理解器

这次重构最重要的定位调整是：

- 规则层保留：
  - hard gate
  - baseline
  - teacher
  - 数据清洗和监督
- 规则层减少：
  - 过度 task 语义承诺
  - staged / planning 的硬编码决定
  - 对所有模糊 query 的最终解释权

这是“规则层失败”吗？

不是。

这是规则层边界终于被识别清楚了。

---

## 5. 为什么这次必须走双轨迁移

### 5.1 现有 V1 资产不能直接推翻

当前仓库里已经有一整套围绕 `V1` 形成的资产：

- 导出样本
- 训练口径
- 评估脚本
- held-out / frozen held-out
- 规则监督与 SFT 交付文档

如果直接覆盖式改写，会同时失去：

- 旧基线
- 回归锚点
- 历史可比性

所以这次的结论很明确：

- `V1` 冻结保留
- `V2` 独立长出来

### 5.2 不是所有历史样本都要返工

这次还确认了一个非常现实的工程结论：

> 大改语义后，最贵也最没必要的动作，往往是“全量手改历史样本”。

更合理的做法是：

- 保留稳定样本
- 局部重标受影响样本
- 让 `V2` 在高风险子集上先收敛

优先重看的，应该是：

- `compound / complex`
- `follow_up / ask_source / challenge / clarify`
- 回答结构容易误判成 staged task 的 query

而不是所有 `qa.generic` 和稳定 `soft_doubt` 全部重做一遍。

### 5.3 双轨迁移的真实好处

双轨迁移不是保守，而是工程上更便宜：

- `V1` 继续提供 baseline
- `V2` 逐步修正语义债
- 两套结果可以直接对比
- 一旦 `V2` 出现偏航，不会把整条训练线一起带崩

所以它的成本虽然看起来更长，但总成本通常更低。

---

## 6. 对后续执行流设计的约束

这次重构经验会直接影响后面的 `workflow` 设计，至少要保留这些约束：

### 6.1 请求理解层不要提前决定全部执行细节

后续即使继续做：

- route
- handling mode
- capabilities

也要记住：

- request understanding 负责理解
- workflow 负责消费理解结果并做执行准备

不能再把 staged / planner / decomposition 一股脑塞回上游。

### 6.2 `query decomposition` 和 `task decomposition` 必须严格区分

后续如果不想再回到现在这种混淆，就必须把两者分清：

- `query decomposition`
  - 更偏 `compound`
  - 更偏 sibling subqueries
- `task decomposition`
  - 更偏 `complex`
  - 更偏 staged work

这是后续执行流模块设计的基础前提。

### 6.3 最终交给主模型的应该是结构化 payload，而不是只有字符串 prompt

这次讨论还收敛出一个重要方向：

- 理想终态不是“上游拼一段 prompt 就结束”
- 而是上游产出一个结构化 `execution payload`

这样可以把：

- 任务理解
- 检索结果
- 子 query
- 输出约束

都清楚交给下游主模型或执行器消费。

---

## 7. 对文档结构本身的经验

### 7.1 这次不建议在 `notes/` 下新开顶层“重构/项目经验”目录

原因很简单：

- 当前 `notes/` 已经有明确分层
- `intent` 相关长期知识在 `notes/intent/`
- 阶段性复盘和执行准备在 `notes/working/intent/`

如果这时单独开一个顶层“重构”目录，反而会把主题打散。

### 7.2 更合理的做法

这次经验文档应该直接放：

- `notes/working/intent/`

等未来类似“跨模块重构复盘”数量明显增多，再考虑是否需要新增：

- `notes/working/project_experience/`
- 或 `notes/working/refactors/`

但在当前阶段，没有必要提前建顶层新目录。

这次优先保证的是：

- 主题聚合
- 阅读路径清晰
- 不额外引入新的目录债

---

## 8. 一句话总结

这次 `evidence / resolver` 重构最重要的经验，不是“怎么把规则写得更复杂”，而是：

> 终于把 `intent` 这一层里，哪些属于“请求理解”，哪些属于“执行决策”，清晰地切开了。

真正值得保留的成果，是这次边界识别本身。
status: active-working
related_current_doc: notes/intent/intent_understanding_architecture.md
scope: evidence resolver refactor lessons
