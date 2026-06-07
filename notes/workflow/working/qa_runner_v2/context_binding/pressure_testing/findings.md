# Context Binding 压测发现

## 说明

这份文档用于记录压测过程中的稳定发现与回归风险。

建议按以下结构追加：

- 样本编号
- 现象
- 根因判断
- 是否需要修复
- 是否纳入回归测试

## 当前状态

已形成第一轮最小样本压测发现。

## Round 1 Findings

### 1. ordinal follow-up 已经相对稳

- 现象：
  - `第二点展开讲讲` 被稳定压到单个 `answer_unit`
  - 直接走 `ordinal_rule`
- 根因判断：
  - `SessionWorkingMemoryResolver._apply_explicit_patterns(...)` 对序号场景处理明确
- 是否需要修复：
  - 否
- 是否纳入回归测试：
  - 已纳入

### 2. 纯弱显式 follow-up / challenge 倾向保守澄清

- 现象：
  - `这个呢`
  - `这个说法有问题`
  - 在多候选场景下都落到 `needs_clarification`
- 根因判断：
  - 当前 relevant set 第一版规则更偏保守，不愿伪造唯一目标
- 是否需要修复：
  - 否，属于当前版本合理行为
- 是否纳入回归测试：
  - 已纳入

### 3. `query_style` 存在一个值得优先修的误判点

- 现象：
  - `working memory 和 memory anchor 的区别是什么`
  - 当前被判成 `multi_target`
  - 后续没有走 `retrieve_on_raw_query`
- 根因判断：
  - `SessionWorkingMemoryResolver.classify_query_style(...)` 把 `和` 作为 `multi_target` 强信号
  - 但这类“对比型自包含问题”实际上更接近 standalone knowledge query
- 是否需要修复：
  - 是
- 是否纳入回归测试：
  - 应补一条黑盒回归

### 4. `challenge` 语义与 `query_style` 不总是同名

- 现象：
  - `你刚才说 challenge 还没完全统一，这个具体指什么`
  - 实际被判成 `follow_up`
  - 但 target resolution 仍然正确
- 根因判断：
  - 当前 `query_style` 更偏“上下文依赖形态分类”
  - 不是 workflow 层的 `handling_mode`
- 是否需要修复：
  - 否，先保留
- 是否纳入回归测试：
  - 建议保留现状说明，不必强改成 `challenge`

### 5. memory anchor 已经能作为 relevant pool 独立来源

- 现象：
  - `daily log` 场景下，单个 `memory_anchor` 可直接进入 relevant set
  - 且不会混成 `working memory entry`
- 根因判断：
  - `ContextBindingPower._build_relevant_pool(...)` 已正确把 `memory_anchor` 视作单独 source kind
- 是否需要修复：
  - 否
- 是否纳入回归测试：
  - 已有基础覆盖，后续可补歧义例

### 6. ChallengePower 已对齐 binding contract，但证据命中仍是单独风险面

- 现象：
  - challenge 已能优先消费 `binding_result`
  - 但在本轮样本中，existing evidence + follow-up retrieval 之后仍然是 `insufficient_evidence`
- 根因判断：
  - target contract 已基本对齐
  - 真正瓶颈转移到 evidence 是否能覆盖 target
- 是否需要修复：
  - 需要继续观察，不应误判成 binding 失败
- 是否纳入回归测试：
  - 建议继续保留 challenge evidence-first 案例

## Round 2 Findings

### 7. “对比型自包含 query 误判成 multi_target” 已修复

- 现象：
  - `working memory 和 memory anchor 的区别是什么`
  - 现在被判成 `standalone`
  - 并走 `retrieve_on_raw_query`
- 根因判断：
  - `query_style` 分类已补上“self-contained comparison”护栏
- 是否需要修复：
  - 否，当前已修
- 是否纳入回归测试：
  - 已纳入

### 8. challenge evidence 已能稳定分出“足够”和“不足”两条消费路径

- 现象：
  - 当 `binding_result` 已给出单个 target，且 existing evidence ref 对齐时，可直接 `success`
  - 当 existing evidence 与 target coverage 不对齐时，会触发 follow-up retrieval，并在不足时返回 `insufficient_evidence`
- 根因判断：
  - `ChallengePower` 已能稳定优先消费 binding contract
  - challenge 当前真正的风险面更多在 evidence coverage，而不是 target recovery
- 是否需要修复：
  - 否，当前行为符合预期
- 是否纳入回归测试：
  - 应持续保留两类 evidence 样本

### 9. 现阶段最值得继续压测的不是 query_style，而是 evidence coverage 质量

- 现象：
  - 第二轮里最关键的分类偏差已经收掉
  - challenge 结果差异现在主要来自 evidence 是否真的覆盖 target
- 根因判断：
  - binding 主链已进入相对稳定区
  - challenge 的下一阶段风险更多是 retrieval/evidence 质量，而非 context binding 结构本身
- 是否需要修复：
  - 不是立即修代码，更适合继续做样本扩充和 evidence 质量压测
- 是否纳入回归测试：
  - 建议在后续压测里增加 evidence-quality 分层样本

## Round 3 Findings

### 10. 真实线程里的自包含架构问法已经能稳定走 raw-query fallback

- 现象：
  - `是不是使用context binding power才能得到relevant set?`
  - `ContextBindingPower应该来自于working_memory / recent candidates / memory_anchors? ...`
  - 都落到 `standalone -> retrieve_on_raw_query`
- 根因判断：
  - 当前自包含对比/结构性问法的分类护栏已经开始生效
- 是否需要修复：
  - 否
- 是否纳入回归测试：
  - 当前可先不再单独扩样本

### 11. 弱显式线程追问仍可能在 query_style 上偏粗，但 relevant set + LLM 能兜住

- 现象：
  - `这不是意图识别的问题吗?`
  - 内部 `query_style` 被判成 `standalone`
  - 但 relevant set 仍构出来了，最终 `llm_resolution` 命中了正确 answer unit
- 根因判断：
  - 当前 `query_style` 规则主要依赖显式 token
  - 这类“这不是...吗”样式没有被很好归入 follow-up
- 是否需要修复：
  - 暂不优先修
- 是否纳入回归测试：
  - 建议作为真实线程样式保留在压测记录中

### 12. `都` 仍然是一个值得留意的 multi_target 误触发词

- 现象：
  - `所以,不管是哪种场景,我们都需要有一个relevant set...`
  - 当前被判成 `multi_target`
  - 最终走 `needs_clarification`
- 根因判断：
  - `multi_target` 规则对 `都` 的依赖仍然偏强
  - 会误伤某些总结型自包含问法
- 是否需要修复：
  - 暂不立刻修，先记录为真实样式风险
- 是否纳入回归测试：
  - 先留在压测记录，不主动继续扩规则

## Round 4 Findings

### 13. live LLM 路径已经真正跑通，但当前环境下没有稳定产出可解析 resolution

- 现象：
  - 使用 `backend/.env` 的真实 provider 配置后，
  - `SessionWorkingMemoryWriter -> ContextBindingPower.bind(...) -> live llm_call`
    已被真实执行
  - 但最终统一落到：
    - `matched_by = fallback`
    - `fallback_type = needs_clarification`
    - `reason = llm_resolution_failed`
- 根因判断：
  - 当前可以确认这不是规则层或 working memory 没走到 live LLM
  - 更像是 live 模型返回没有稳定满足当前 JSON parser / validator，或当前网络/连通性导致模型结果未成功返回
- 是否需要修复：
  - 需要继续观察，但它属于 live LLM 运行面问题，不是 `Context Binding` 规则主链 blocker
- 是否纳入回归测试：
  - 已纳入 live smoke 黑盒测试

### 14. 当前 live LLM 压测结果不能证明“真实模型质量可接受”，只能证明“真实模型路径已执行”

- 现象：
  - fake/stub 测试里 `llm_resolution` 能稳定出现
  - real live smoke 里，目前只确认路径执行，不确认质量
- 根因判断：
  - 当前真实压测暴露的是 external/runtime 面不稳定性
  - 不是 workflow 内部 typed contract 或 relevant set 主链失效
- 是否需要修复：
  - 不是本轮立即改 workflow 规则能解决的问题
- 是否纳入回归测试：
  - 保留 live smoke，作为后续环境恢复后的直接验证入口

## 当前压测结论

- `Context Binding` 前两轮压测已经证明主链能跑：
  - `relevant pool -> relevant set -> 规则直出 / 大模型 resolution / fallback`
- 当前已完成的关键修复：
  - “对比型自包含 query 被误判成 multi_target”的分类问题
- 当前不建议把“challenge 证据不足”解读为 binding 问题：
  - 这更多是 evidence coverage 问题
- 当前真实样式里仍存在的可接受粗糙点：
  - 弱显式线程追问的 `query_style` 可能偏粗
  - `都` 仍可能误触发 `multi_target`
  - 但在当前策略下，这些先记录，不继续高成本扩规则
- 当前新增观察点：
  - live LLM 路径已执行，但真实模型结果当前未稳定落成可解析 resolution
  - 这更像环境/运行面问题，而不是 `Context Binding` 规则主链噪音失控

## 当前样本策略结论

- 后续压测以当前线程近 20 轮真实对话样式为主
- 暂不继续大规模补人工样本
- 只有当真实压测再次暴露出明确 blocker 时，才按需补最小样本

这样做的理由是：

- 当前真实样式已经足够暴露 `Context Binding` 主链里的主要问题
- 继续扩样本的代价较高
- 当前阶段更需要稳定迭代压测结论，而不是追求形式上的样本大全

## 当前剩余问题分级

### Blocker

- 当前未发现新的 workflow 范围内 blocker
- 已修复的 blocker：
  - “对比型自包含 query 被误判成 `multi_target`”

### 可接受粗糙点

- 弱显式线程追问的 `query_style` 仍可能偏粗
  - 例如：`这不是意图识别的问题吗?`
  - 当前会更依赖 `relevant set + llm_resolution` 兜住目标恢复
- `都` 仍可能误触发 `multi_target`
  - 例如总结型自包含问法
  - 当前记录为真实样式风险，不继续高成本扩规则

### 后续观察点

- challenge 路径当前更值得继续观察的是 evidence coverage
- 这属于 challenge / retrieval 质量面，不应回头误判为 context binding 主链 blocker
