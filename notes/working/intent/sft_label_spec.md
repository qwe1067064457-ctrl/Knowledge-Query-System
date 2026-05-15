# Intent SFT Label Spec

## 1. 文档定位

这份文档用于冻结 `intent` 小模型第一版的标签范围。

当前目标不是定义一个“完整 intent 全家桶”，而是定义一个**足够轻、足够稳、能验证小模型是否对规则层有增益**的 v1 标签集合。

这是一份 working 文档，当前重点是：

- 先防止后续样本扩充越长越乱
- 先明确第一版训什么，不训什么
- 先给数据标注和训练脚本一个稳定接口

---

## 2. 第一版训练目标

### 2.1 当前阶段判断

当前样本明显不足以支撑完整 `intent` SFT。

因此第一版不追求：

- 完整 `main_intent` 多分类
- 全量 modifiers
- 全量 `task.shape`
- `control.route / control.mode` 直接预测

第一版更现实的目标是：

- 用一个轻量 classifier 验证：
  - 是否能补规则层的开放表达盲区
  - 是否能提升 `soft_doubt` 这类边界语义
  - 是否能帮助区分关键 shape 边界

### 2.2 第一版建议任务

建议先做两个头：

1. `soft_doubt` 二分类
2. `task.shape` 小集合分类

`main_intent` 暂不作为正式训练目标。

如果需要保留 `main_intent` 字段，也只作为数据字段存在，不进入第一版正式结果比较。

---

## 3. 标签定义

### 3.1 头 1：`soft_doubt`

任务形式：

- 二分类

标签：

- `true`
- `false`

定义：

- `true`
  - 轻质疑
  - 弱反驳
  - 求证式保留
  - 不直接说“你错了”
  - 常带上下文回指
- `false`
  - 普通 QA
  - 普通 follow-up
  - 明确 hard challenge
  - 纯情绪表达
  - ask_source / ask_capability / unsupported

注意：

- “有不确定语气”不等于 `soft_doubt`
- 普通 QA 中的“是不是”“是否”不能自动标成 `soft_doubt`

### 3.2 头 2：`task.shape`

任务形式：

- 单标签多分类

第一版标签集合：

- `single_question`
- `verify`
- `compare`
- `summarize`
- `multi_question`

当前不纳入第一版正式训练的 shape：

- `mixed`
- `extract`
- 其他仍不稳定或样本过少的细分 shape

原因：

- `mixed` 更像保底收敛类，不适合第一版拿来做稳定监督
- `extract` 当前样本不足，边界也未冻结

---

## 4. 当前暂不训练的字段

第一版暂不训练：

- `main_intent`
- `challenge`
- `follow_up`
- `ask_source`
- `needs_clarification`
- `control.route`
- `control.mode`

原因：

- 当前 gold 分布严重不完整
- 很多字段还缺足够正负样本
- 这些任务一起上只会放大噪声

---

## 5. 标签来源约束

### 5.1 可以直接进入训练的标签

- 人工确认的四层 gold
- 冻结后的明确 `task.shape`
- 明确 `soft_doubt` 标注

### 5.2 不应直接作为第一版高权重监督的标签

- 仅规则推断得到的 `soft_doubt`
- 未复核的 `task.shape`
- 由 `control` 反推出来的标签

---

## 6. 标注规则

### 6.1 `soft_doubt`

标 `true` 的最低条件：

- 语句存在弱质疑或求证语气
- 不是普通知识型提问
- 不是明确 hard disagree
- 最好带回指或上下文依赖

### 6.2 `task.shape`

标注优先级：

1. 先判断主任务动作
2. 如果 query 既像解释又像判断，优先看最终业务诉求
3. 如果无法稳定压成单一 shape，不勉强塞进第一版训练集

---

## 7. 当前缺口

当前要让这个 label spec 变成真正可训练版本，至少还要补：

- 更多 `compare` 正例
- 更多 `summarize` 正例
- `multi_question` 正例
- `soft_doubt=false` 的高质量边界负例

---

## 8. 当前结论

第一版小模型标签先冻结成：

- `soft_doubt` 二分类
- `task.shape` 五分类

等样本明显增厚、split 固定、baseline 跑通后，再决定是否扩到：

- `main_intent`
- 更多 modifiers
- 多头联合训练
