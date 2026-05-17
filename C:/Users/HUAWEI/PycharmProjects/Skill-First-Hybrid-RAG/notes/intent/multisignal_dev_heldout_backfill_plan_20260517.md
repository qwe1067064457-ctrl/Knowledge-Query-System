# Multi-Signal Dev/Heldout Backfill Plan 2026-05-17

## 1. 当前事实

当前多信号 SFT v1 关注的 6 个边界信号为：

- `soft_doubt`
- `follow_up`
- `needs_clarification`
- `ask_source`
- `multi_question`
- `complex`

当前 `gold` split 覆盖如下：

### train

- `soft_doubt=9`
- `follow_up=10`
- `needs_clarification=3`
- `ask_source=11`
- `multi_question=15`
- `complex=8`

### dev

- `needs_clarification=2`
- 其余 5 个均为 `0`

### heldout

- `soft_doubt=3`
- 其余 5 个均为 `0`

这意味着：

- 现有 `dev` 不能用于 6 信号多标签调参
- 现有 `heldout` 不能用于 6 信号最终比较
- 当前问题不在模型容量，而在评估集覆盖失真

## 2. 冻结约束

- 不修改现有 `backend_test/intent/test_data/gold/frozen/frozen_heldout_v2`
- `frozen_heldout_v2` 继续作为历史冻结 benchmark 保留
- 本轮新增评估集使用新的 `heldout_v3`
- `campaign` 数据不直接进入 benchmark，必须先人工 uplift 为 `gold`
- `silver` 只能作为候选池，不直接进入 `dev` 或 `heldout_v3`

## 3. 本轮目标

### dev 目标

把 6 个信号都补到最少可调参状态。

目标下限：

- 每个 signal 至少 `4` 个正例
- 每个 signal 至少 `2` 个 hard negative

按当前差额，本轮最少新增：

- `soft_doubt +4`
- `follow_up +4`
- `needs_clarification +2`
- `ask_source +4`
- `multi_question +4`
- `complex +4`

合计最少新增 `22` 条正例。

### heldout_v3 目标

新建覆盖完整的冻结集，不沿用 `frozen_heldout_v2` 的标签分布。

目标下限：

- 每个 signal 至少 `5` 个正例
- 每个 signal 至少 `3` 个 hard negative`

建议 `heldout_v3` 采用全新人工确认 gold，不混入历史 frozen。

## 4. 信号级补数策略

### 4.1 `follow_up`

目标：

- 补“依赖历史但当前问句不自足”的追问

优先来源：

1. `evaluation/intent/query_inputs/seed_query_20260515_router_augmented.jsonl`
   - `label=follow_up`
   - 当前 5 条，可优先 uplift
2. `backend_test/intent/test_data/gold/silver/seed_query_20260515_campaign_v2_silver_v1/follow_up.json`
   - 当前 25 条
   - 优先挑 `*_supportive` 变体
3. `backend_test/intent/test_data/gold/silver/intent_query_full_set_campaign_v1_silver_v1/follow_up.json`
   - 当前 475 条
   - 仅作补量池，不直接整包提样

筛选约束：

- 只保留带真实 `history` 的样本
- 不把 `*_weak` 变体误提为 `follow_up` 正例
- 裸句如“那这种情况呢？”只适合作 `needs_clarification` 候选，不适合作高质量 `follow_up` benchmark

### 4.2 `ask_source`

目标：

- 补“明确追问依据、法条、出处、原文”的样本

优先来源：

1. `evaluation/intent/query_inputs/seed_query_20260515_router_augmented.jsonl`
   - `label=ask_source`
   - 当前 3 条
2. `backend_test/intent/test_data/gold/silver/seed_query_20260515_campaign_v2_silver_v1/meta.json`
   - 当前 9 条
   - 质量优先于大池
3. `backend_test/intent/test_data/gold/silver/query_list_campaign_v1_silver_v1/meta.json`
   - 当前 3 条

筛选约束：

- 不直接使用过短问句，如“有依据吗？”
- 优先保留带上文锚点的问法
- `ask_source` 与 `complex` 不混用，除非样本本身确实包含多动作请求

### 4.3 `soft_doubt`

目标：

- 补“弱质疑、委婉质疑、保留判断”的样本

优先来源：

1. `evaluation/intent/query_inputs/seed_query_20260515_router_augmented.jsonl`
   - `label=soft_doubt`
   - 当前 4 条
2. `backend_test/intent/test_data/gold/train/seed_query_20260516_gold_v1/soft_doubt_boundary_seed.json`
   - 当前 8 条
   - 可抽一部分改写后进入新 split
3. `backend_test/intent/test_data/gold/silver/seed_query_20260515_campaign_v2_silver_v1/challenge.json`
   - 当前 16 条
   - 优先取 `required_signals` 含 `soft_doubt` 且语气明显偏弱的样本

筛选约束：

- 不把强反驳句当作 `soft_doubt`
- 优先保留“我不太确定 / 会不会太绝对 / 是不是还要看”的语气
- 对显式冲突、否定性很强的句子，保留到 `challenge` 线，不放进本 benchmark

### 4.4 `multi_question`

目标：

- 补“一问多子问 / 并列追问 / 连续任务”的样本

优先来源：

1. `evaluation/intent/query_inputs/seed_query_20260515_router_augmented.jsonl`
   - `label=multi_question`
   - 当前 3 条
2. `backend_test/intent/test_data/gold/train/seed_query_20260515_gold_v2/multi_question_seed.json`
   - 当前 6 条
3. `backend_test/intent/test_data/gold/silver/intent_query_full_set_campaign_v1_silver_v1/mixed_intent.json`
   - 当前 6 条
   - 只取其中主导语义明确是一问多问的样本

筛选约束：

- 避免把“长单问句”误标成 `multi_question`
- 句内必须存在两个以上明确子问题或子任务

### 4.5 `complex`

目标：

- 补“需要规划、综合、分步骤分析”的样本

优先来源：

1. `backend_test/intent/test_data/gold/silver/intent_query_full_set_campaign_v1_silver_v1/long_case_complex.json`
   - 当前 38 条
   - 第一优先
2. `backend_test/intent/test_data/gold/silver/seed_query_20260515_campaign_v2_silver_v1/challenge.json`
   - 当前部分样本 `required_signals` 含 `complex`
3. 新写少量人工 seed
   - 用于补纯 `complex` 而非“复杂 + ask_source”混合样本

筛选约束：

- 不从 `meta.json` 直接提 `complex`
- 复杂度必须来自任务结构，不来自句长
- 优先保留确实需要多步判断的样本

### 4.6 `needs_clarification`

目标：

- 补“指代不清 / 对象不清 / 前提缺失”的样本

当前事实：

- 现有显式 `dev` 只有 2 条
- 候选池里这类样本最少，不能只靠现有 silver

优先来源：

1. 复用 `follow_up` 候选里的 `missing_history` / `*_weak` 变体
2. 新写人工 seed
   - 优先补：
   - 指代词缺失
   - 范围不清
   - 主题未锚定
   - 缺关键前提

筛选约束：

- 不是短句就算 clarify
- 必须是“在不补前提前无法安全检索或回答”

## 5. 建议的新文件落点

### query 输入层

- `evaluation/intent/query_inputs/seed_query_20260517_router_augmented_v2.jsonl`
  - 存本轮新增或改写后的边界 query
  - 文件名带日期，避免覆盖旧资产

### dev gold

- `backend_test/intent/test_data/gold/dev/seed_query_20260517_gold_v2/`

建议拆文件：

- `follow_up_seed.json`
- `ask_source_seed.json`
- `soft_doubt_seed.json`
- `multi_question_seed.json`
- `complex_seed.json`
- `clarify_seed.json`

### heldout gold

- `backend_test/intent/test_data/gold/frozen/frozen_heldout_v3/`

建议拆文件：

- `follow_up_frozen.json`
- `ask_source_frozen.json`
- `soft_doubt_frozen.json`
- `multi_question_frozen.json`
- `complex_frozen.json`
- `clarify_frozen.json`

## 6. 执行顺序

1. 从 `router_augmented` 和 `silver` 候选中各 signal 初筛候选
2. 先产出 `dev` 正例和 hard negative
3. 人工 uplift 为 `gold/dev`
4. 再单独构造 `heldout_v3`
5. 冻结 `heldout_v3` 后再重导出 multisignal bundle
6. 最后重跑 `macbert` baseline

## 7. 本轮执行建议

先做两件事，不要并行扩太散：

1. 优先补 `dev`
   - 因为当前 `dev` 对 6 个 signal 几乎不可用
2. 在补 `dev` 的同时，开始起草 `heldout_v3`
   - 但 `heldout_v3` 只收人工确认 gold，不直接收 silver 提样

## 8. 直接可用的候选入口

### 适合直接开始 uplift 的来源

- `evaluation/intent/query_inputs/seed_query_20260515_router_augmented.jsonl`
- `backend_test/intent/test_data/gold/silver/seed_query_20260515_campaign_v2_silver_v1/follow_up.json`
- `backend_test/intent/test_data/gold/silver/seed_query_20260515_campaign_v2_silver_v1/meta.json`
- `backend_test/intent/test_data/gold/silver/seed_query_20260515_campaign_v2_silver_v1/challenge.json`
- `backend_test/intent/test_data/gold/silver/intent_query_full_set_campaign_v1_silver_v1/long_case_complex.json`

### 只适合作大池补量，不适合直接进 benchmark 的来源

- `backend_test/intent/test_data/gold/silver/intent_query_full_set_campaign_v1_silver_v1/follow_up.json`
- `backend_test/intent/test_data/gold/silver/intent_query_full_set_campaign_v1_silver_v1/meta.json`

原因：

- 重复度高
- 模板痕迹重
- 短句过多
- 容易造成 `follow_up / clarify` 或 `ask_source / complex` 串味

## 9. 结论

当前正确动作不是继续解释模型指标，而是：

1. 保持 `frozen_heldout_v2` 不动
2. 新建 `heldout_v3`
3. 先把 6 个边界 signal 的 `dev` 覆盖补齐
4. 再补齐 `heldout_v3`
5. 最后重跑多信号 baseline
