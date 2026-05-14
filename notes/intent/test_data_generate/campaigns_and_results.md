# Intent 测试数据 Campaign 记录

## 1. 这份文件的用途

这份文件专门记录当前已经跑过的测试数据 campaign、各自的目标、结果和它们打出来的规则问题。

它不追求记录所有历史细节，而是帮助后续快速回答：

- 这批样本是干什么的
- 它有没有真正把系统打疼
- 它主要暴露了哪几条规则的边界问题

---

## 2. `v1_adversarial_campaign`

### 2.1 目标

第一批高价值对抗闭环，重点打：

- `follow_up`
- `challenge`

并优先使用：

- `near_miss`
- `mixed`

### 2.2 作用

它的核心任务不是覆盖全面，而是先证明：

> 对抗样本生成器产出的数据，确实能让原本好看的指标掉下来。

### 2.3 结果信号

它最早证明了几件事：

- `challenge` 的规则召回偏低
- `follow_up` 的上下文依赖处理不稳
- 单看干净样本时高分并不可信

这批 campaign 的意义更像：

> 让系统第一次从“顺风测试”进入“逆风测试”。

---

## 3. `query_list_campaign_v1`

### 3.1 目标

验证：

> 原始 query -> 四层草稿 -> history 变体 -> 评估报告

这条链到底能不能跑通。

### 3.2 输入来源

使用了 5 条真实风格 query 作为 benchmark 输入，经过 `from_query_list` 派生为 16 条样本。

### 3.3 结果

它已经让这些指标明显掉下来了：

- `resolved_main_intent_accuracy = 0.5`
- `control_route_accuracy = 0.3125`

### 3.4 它暴露了什么

重点掉点：

- `follow_up`
- `fuzzy_qa`
- `mixed_intent`

它证明了：

> `from_query_list` 不是演示功能，而是能从真实 query 素材出发，稳定产出能打到规则边界的测试草稿。

---

## 4. `twins_campaign_v2`

### 4.1 目标

专门做“近邻双胞胎”边界压测：

- `challenge vs clarify`
- `follow_up vs ambiguous`
- `qa vs system`

### 4.2 第一轮结果

在规则修复前，它打出的结果非常尖锐：

- `control_route_accuracy = 0.1667`
- `resolved_main_intent_accuracy = 0.5`

当时暴露出的核心问题：

1. `challenge.disagree`
   - 高精确，低召回
2. `context.follow_up.reference`
   - 过敏，精确率低
3. `context.follow_up.missing_history`
   - 缺失
4. `system.capability.ask`
   - 几乎没接住

### 4.3 第一轮修规则后复跑结果

复跑后的整体结果：

- `resolved_main_intent_accuracy = 0.6667`
- `control_route_accuracy = 0.5`
- `control_mode_accuracy = 0.7083`

规则层变化最关键的是：

#### `challenge.disagree`

- 修复前：
  - `precision = 1.0`
  - `recall = 0.25`
- 修复后：
  - `precision = 1.0`
  - `recall = 0.5`

结论：
- 召回翻倍
- 没引入新的误报

#### `context.follow_up.reference`

- 修复前：
  - `precision = 0.5`
  - `recall = 1.0`
- 修复后：
  - `precision = 1.0`
  - `recall = 1.0`

结论：
- 上下文过敏被明显收住

#### `context.follow_up.missing_history`

- 修复前：
  - `precision = 0.0`
  - `recall = 0.0`
- 修复后：
  - `precision = 1.0`
  - `recall = 1.0`

结论：
- “缺 history 时要澄清”这条规则终于立住了

#### `system.capability.ask`

- 修复前：
  - `precision = 0.0`
  - `recall = 0.0`
- 修复后：
  - `precision = 1.0`
  - `recall = 0.75`

结论：
- `qa vs system` 这条边界已经不再裸奔

### 4.4 它现在仍然在提醒什么

虽然 v2 已经明显改善，但还有两块没修透：

1. `challenge`
   - 软表达仍然不够稳
2. `standard_qa`
   - 业务锚点还偏弱

所以 v2 的下一阶段价值，是继续做：

- `challenge` 软表达扩展
- `standard_qa` 业务问法锚点补强

---

## 5. 当前 campaign 使用建议

### 5.1 想看规则是否回归

优先跑：

- `v1_adversarial_campaign`
- `twins_campaign_v2`

### 5.2 想看原始 query 派生能力是否稳定

优先跑：

- `query_list_campaign_v1`

### 5.3 想压某一条边界

优先做：

- twin pair
- near_miss
- conflicting history

而不是先堆大量 clean QA。

---

## 6. 当前结论

到目前为止，最重要的结论不是“我们已经有很多测试数据”，而是：

> 我们已经有能力用少量但锋利的对抗 campaign，把 `intent` 模块里真正脆弱的规则边界持续打出来，并用同一批资产验证修复是否有效。

