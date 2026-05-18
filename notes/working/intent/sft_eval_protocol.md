# Intent SFT Eval Protocol

## 1. 文档定位

这份文档定义 `intent` 小模型第一版的评估协议。

当前目标不是做一套非常重的评测体系，而是用最小协议回答两个问题：

1. 小模型有没有学到东西
2. 小模型是否对纯规则有“超规则价值”

---

## 2. 当前 baseline 对象

第一版比较对象不是“大模型”，而是：

- 当前规则层
- 未来的轻量 encoder classifier baseline

当前建议模型：

- `hfl/chinese-macbert-base`

---

## 3. 第一版评估目标

第一版不追求“完整 intent 全家桶总分”。

优先评估：

1. `soft_doubt`
2. `task.shape`

如果第一版只训练这两个头，那么评估协议也先围绕这两个头定义。

---

## 4. 指标定义

### 4.1 `soft_doubt`

主指标：

- `precision`
- `recall`
- `f1`

重点关注：

- held-out 上的 `recall`

原因：

- 当前规则层最容易在开放表达下漏掉 `soft_doubt`
- 所以模型是否补 recall，比训练集高分更重要

### 4.2 `task.shape`

主指标：

- `accuracy`
- `macro_f1`

辅助指标：

- per-class recall
- confusion matrix

重点关注：

- `verify` 与 `single_question` 是否更稳
- `compare / summarize / multi_question` 是否开始有可用信号

---

## 5. split 使用方式

### 5.1 `train`

只用于训练

### 5.2 `dev`

只用于：

- early stopping
- 选 epoch
- 比较不同超参
- 比较不同 encoder baseline

### 5.3 `heldout`

只用于：

- 每一轮训练完成后的最终验证

不允许：

- 根据 held-out 表现继续来回调参数
- 根据 held-out 改标签定义
- 根据 held-out 改 split

---

## 6. 当前最小评估输出

每次 baseline 至少产出：

### 6.1 `soft_doubt`

- train 指标
- dev 指标
- held-out 指标
- held-out 错例列表

### 6.2 `task.shape`

- train accuracy / macro F1
- dev accuracy / macro F1
- held-out accuracy / macro F1
- held-out confusion matrix

---

## 7. 当前“超规则价值”判断标准

第一版 baseline 不看训练集 acc，不看是否把样本记住。

真正要看的，是 held-out 上有没有以下改进：

### 7.1 `soft_doubt`

- recall 高于当前纯规则
- precision 不出现明显崩塌

### 7.2 `task.shape`

- `verify / single_question` 边界更稳
- 对开放表达的 shape 漏判更少

如果模型只是把训练集拟合得很好，但 held-out 没比规则好，就不算成功。

---

## 8. 当前不建议看的伪指标

第一版不要过度关注：

- 训练集高分
- 微小样本上的总体 accuracy
- probe 结果的偶然波动

原因：

- 当前样本量太小
- 分布还不完整
- 很容易被过拟合误导

---

## 9. 报告结构建议

每次 baseline 建议输出 4 段：

1. 本轮训练配置
2. dev 指标
3. held-out 指标
4. 典型错误分析

如果没有错误分析，指标本身的信息量会非常有限。

---

## 10. 当前结论

第一版评估协议的核心不是“追总分”，而是回答：

> 在冻结 held-out 上，这个轻量模型是否能比纯规则更少漏掉 `soft_doubt`，并且在关键 `task.shape` 边界上更稳。
status: active-working
related_current_doc: notes/intent/test_data_generate/README.md
scope: sft eval protocol
