# Intent 测试数据打通说明

## 1. 这份目录在记录什么

这个目录专门记录 `intent` 模块在“测试数据生成与打通”上的工作，不讨论执行流优化，也不重复四层 schema 的基础定义。

这里关心的是一条完整链路：

```text
原始 query / 规则目标
  -> 对抗样本生成
  -> 四层草稿补全
  -> 评估脚本运行
  -> overall / per_batch / rule_stats 出结果
  -> 反推规则修正
```

也就是说，我们现在做的不只是“补一些样本”，而是在搭一条可复用的测试工作流。

### 1.1 新增：面向 SFT 的数据生成经验

如果当前关注的是：

- `campaign`
- `four-layer draft`
- `silver`
- `gold`
- 为什么样本很多但可训练成品不多
- 为什么要走 `seed -> campaign -> silver -> gold`

优先读：

- [sft_preparation_data_generation_lessons.md](C:/Users/HUAWEI/.codex/worktrees/2a18/Skill-First-Hybrid-RAG/notes/intent/test_data_generate/sft_preparation_data_generation_lessons.md)

---

## 2. 当前已经打通的能力

### 2.1 基础评估链路

当前已经具备：

- 四层评估结构：
  - `input`
  - `evidence`
  - `resolved`
  - `control`
- 评估脚本：
  - [C:\Users\HUAWEI\PycharmProjects\Skill-First-Hybrid-RAG\evaluation\intent\evaluate_intent_rules.py](/C:/Users/HUAWEI/PycharmProjects/Skill-First-Hybrid-RAG/evaluation/intent/evaluate_intent_rules.py)
- 按层输出：
  - `overall`
  - `per_batch`
  - `rule_stats`

### 2.2 对抗样本生成 skill

当前 skill：

- [C:\Users\HUAWEI\PycharmProjects\Skill-First-Hybrid-RAG\skills\adversarial-intent-test-generator\SKILL.md](/C:/Users/HUAWEI/PycharmProjects/Skill-First-Hybrid-RAG/skills/adversarial-intent-test-generator/SKILL.md)

当前脚本：

- [C:\Users\HUAWEI\PycharmProjects\Skill-First-Hybrid-RAG\skills\adversarial-intent-test-generator\scripts\scaffold_intent_dataset.py](/C:/Users/HUAWEI/PycharmProjects/Skill-First-Hybrid-RAG/skills/adversarial-intent-test-generator/scripts/scaffold_intent_dataset.py)

当前已经支持：

- `empty`
- `v1_adversarial_campaign`
- `from_query_list`
- `twins_campaign_v2`

### 2.3 生成模式

当前生成器已经支持：

- `positive`
- `negative`
- `near_miss`
- `mixed`
- `cost_focused`

其中真正高价值的是：

- `near_miss`
- `mixed`
- `cost_focused`

---

## 3. 当前为什么要做测试数据打通

我们已经验证过一个很重要的事实：

> 如果测试集太干净、太顺着规则写，`precision / recall` 会假高。

所以当前这条线的目标不是“多造点样本”，而是：

1. 让样本来源更真实  
   也就是从业务 query 或类业务 query 出发，而不是只靠手写规则样本。

2. 让样本更会打边界  
   尤其是：
   - `follow_up`
   - `challenge`
   - `mixed_intent`
   - `qa vs system`
   - `fuzzy_qa`

3. 让评估结果能直接反推规则  
   不是只看总分，而是能回答：
   - 哪条规则过敏
   - 哪条规则漏召回
   - 哪个 batch 最容易把路由打偏

---

## 4. 当前工作流

### 4.1 路径 A：预设 campaign

适合做固定回归和高价值攻击集：

```text
指定 profile
  -> 生成固定批次样本
  -> 写入 backend_test/intent/test_data/<campaign>
  -> 跑 evaluation/intent/evaluate_intent_rules.py
  -> 观察规则掉点
```

当前代表：

- `v1_adversarial_campaign`
- `twins_campaign_v2`

### 4.2 路径 B：原始 query 驱动

适合把手头已有 query 迅速转成结构化测试资产：

```text
准备 txt/json/jsonl query 列表
  -> 用 from_query_list 入口喂给 skill
  -> 自动派生 supportive / weak / conflicting history
  -> 自动派生 near_miss / mixed / cost_focused
  -> 自动补四层草稿和 risk_flags
  -> review 后进入正式测试集
```

当前代表：

- `query_list_campaign_v1`

---

## 5. 当前已经形成的测试资产

### 5.1 query_list_campaign_v1

位置：

- [C:\Users\HUAWEI\PycharmProjects\Skill-First-Hybrid-RAG\backend_test\intent\test_data\query_list_campaign_v1](/C:/Users/HUAWEI/PycharmProjects/Skill-First-Hybrid-RAG/backend_test/intent/test_data/campaign/query_list_campaign_v1)

特点：

- 从 5 条真实风格 query 出发
- 自动扩成 16 条样本
- 混合了：
  - `follow_up`
  - `challenge`
  - `meta`
  - `fuzzy_qa`
  - `mixed_intent`

它证明了一件事：

> `from_query_list` 已经不是演示能力，而是能真正产出“改改就能用”的测试草稿。

### 5.2 twins_campaign_v2

位置：

- [C:\Users\HUAWEI\PycharmProjects\Skill-First-Hybrid-RAG\backend_test\intent\test_data\twins_campaign_v2](/C:/Users/HUAWEI/PycharmProjects/Skill-First-Hybrid-RAG/backend_test/intent/test_data/experiments/twins_campaign_v2)

特点：

- 只做近邻双胞胎
- 总量不大，但攻击性强
- 重点打三个边界：
  - `challenge vs clarify`
  - `follow_up vs ambiguous`
  - `qa vs system`

它的意义是：

> 用极少量但极贴边的样本，把规则系统真正的结构性盲区打出来。

---

## 6. 当前生成器里的关键设计

### 6.1 不是全自动真值器，而是半自动草稿器

当前 skill 的定位已经明确：

> 它是半自动对抗样本草稿生成器，不是最终 gold 真值生产器。

它自动做：

- 派生 query
- 派生 history
- 预填 `gold.evidence`
- 预填 `gold.resolved`
- 预填 `gold.control`
- 添加 `review_hints`

人工仍然要做：

- 快速 review
- 修正逻辑断裂的样本
- 决定哪些样本进正式测试库

### 6.2 先定 resolved/control，再反推 evidence

这是当前样本生成的重要策略。

不是先自由写一句 query 再猜标签，而是先决定：

- 这题最终应该是什么意图
- 应该走哪条 control 路由

再反推：

- 系统至少要识别到哪些 signal
- 哪些 rule expectation 必须被命中

这样做的目的是：

> 定向命题，而不是自由作文。

### 6.3 history 不是随便补的

当前 history 模板有三类：

- `supportive`
- `weak`
- `conflicting`

作用分别是：

- `supportive`：验证基础召回
- `weak`：逼出 `needs_clarification`
- `conflicting`：测试是否因为“有历史就硬关联”

### 6.4 risk_flags 是轻量自检

当前生成器会自动打一些风险标记，帮助人工 review：

- `INPUT_TOO_WEAK`
- `HISTORY_SUPPORT_UNCLEAR`
- `CONTROL_ROUTE_COST_RISK`
- `REDUNDANT_HISTORY_FOR_NON_DEP_SAMPLE`
- `ROUTE_INTENT_MISMATCH`
- `POSSIBLE_COMPLEX_TASK_MISS_ROUTED`

这些不是最终判决，但很适合做第一轮筛查。

---

## 7. 当前打通测试用例之后，最直接带来的价值

### 7.1 能更快地从“样本”走到“规则修复”

以前的问题是：

- 规则改了
- 缺少足够尖锐的样本验证
- 看上去都挺对
- 上线后才暴露边界问题

现在的流程变成：

```text
生成 hard set
  -> 跑评估
  -> 看 per_batch 和 rule_stats
  -> 锁定具体规则
  -> 修规则
  -> 重跑 campaign 验证是否真的变好
```

### 7.2 能看到“错的成本”

当前我们不只看：

- 分对没分对

还看：

- 错了以后是不是把复杂问题掉进简单流
- 错了以后是不是把 system / unsupported 混进 QA
- 错了以后是不是让 challenge 丢掉验证流

这就是 `cost_focused` 模式的价值。

### 7.3 能专门拷打 resolver 和 control

以前很多样本只会验证 `main_intent`。

现在我们已经能系统性地验证：

- `resolved.task`
- `context_dependency`
- `control.route`
- `control.mode`

这让“分流架构”本身也开始可测。

---

## 8. 当前这条线最值得继续盯的指标

以后每次补样本或修规则，建议优先看：

### 8.1 overall

- `resolved_main_intent_accuracy`
- `control_route_accuracy`
- `control_mode_accuracy`

### 8.2 per_batch

重点批次：

- `follow_up`
- `challenge`
- `meta`
- `mixed_intent`
- `standard_qa`

### 8.3 rule_stats

重点规则：

- `challenge.disagree`
- `context.follow_up.reference`
- `context.follow_up.missing_history`
- `system.capability.ask`

如果这些规则在 hard set / twins set 上开始有明显改善，就说明我们这条链真的在产生工程收益。

---

## 9. 当前建议的使用顺序

### 场景 1：想看规则是否回归

先跑：

- `v1_adversarial_campaign`
- `twins_campaign_v2`

### 场景 2：手头有一批新 query

先跑：

- `from_query_list`

生成草稿后：

- 先看 `review_hints.risk_flags`
- 再挑出能进正式集的样本

### 场景 3：想专门拷打某条边界

优先补：

- twin pairs
- near_miss
- conflicting history

而不是先补大量 clean QA。

---

## 10. 一句话总结

当前 `notes/intent/test_data_generate` 这条线记录的，不是“如何多造点测试数据”，而是：

> 如何把 `intent` 模块的测试用例真正打通成一条工程闭环：从 query 来源、到对抗样本加工、到四层草稿补全、到评估指标、再到规则修复与回归验证。

