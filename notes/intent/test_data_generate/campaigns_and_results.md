# Campaigns and Results

## 1. 这篇文档讲什么

这篇文档按阶段整理：

- 每一批数据为什么生成
- 典型 campaign 是什么
- 它解决了什么问题
- 最后沉淀成了什么资产

## 2. 第一批：Rule Tuning 数据

### 目标

- 为 rule 层调优服务
- 快速暴露边界问题
- 支持 rule supervision

### 典型 campaign

- `v1_adversarial_campaign`
- `query_list_campaign_v1`
- `twins_campaign_v2`

### 重点攻击的边界

- `follow_up`
- `challenge`
- `clarify`
- `qa vs system`
- `qa vs chat`
- `mixed_intent`
- `near_miss`

### 这批数据的价值

- 让 rule 调优不再只靠直觉
- 让 per-batch 评估开始变得有意义
- 让“命中质量问题”和“设计问题”可以拆开看

## 3. 第二批：SFT / 小模型准备数据

### 目标

- 把 understanding 结果转成可训练标签
- 为小模型准备 `main_intent / modifiers / task` 监督
- 为 heldout / export / delivery 打基础

### 重点工作

- 结构化标签规范
- split policy
- eval protocol
- gold expansion
- training export

### 这批数据的价值

- 让 rule 不只是在线上硬判，还能作为 teacher
- 让小模型后续接管中层理解成为可能

## 4. 第三批：V2 Migration 数据

### 目标

- 支撑 `V2` 新口径
- 支撑 `V2 auto`
- 支撑新 taxonomy 与新 resolver 结构

### 重点工作

- `V2 auto annotations`
- `V1 vs V2 auto diff`
- `quality gate`
- `V2 topology export`
- migration candidate filtering

### 这批数据的价值

- 让 understanding 重构有可观测的数据线
- 让新旧语义可以并行验证
- 让双轨迁移成为工程化过程，而不是一次性翻盘

## 5. 典型 campaign 的历史意义

### `v1_adversarial_campaign`

意义：

- 打规则层
- 建立第一波系统性边界攻击样本

### `query_list_campaign_v1`

意义：

- 让真实 query 风格更快进入评估链
- 减少“样本太像规则”的问题

### `twins_campaign_v2`

意义：

- 用极贴边 pair 去打结构性盲点
- 对 `clarify / challenge / qa-system` 很有价值

## 6. 当前应该怎么理解这些结果

不是每一个 campaign 都还等价重要。

当前更推荐这样理解：

### 第一批结果

用于回答：

- rule 层到底哪里脆
- 哪些边界是命中问题
- 哪些是设计问题

### 第二批结果

用于回答：

- 小模型未来能吃什么标签
- 当前 teacher 资产够不够用

### 第三批结果

用于回答：

- `V2` 改了什么
- 新旧迁移是否健康
- `quality gate` 是否过关

## 7. 当前一句话总结

当前这些 campaign 和结果，最好不要再按“零散实验”理解，而应该按：

> 第一批调 rule、第二批备 SFT、第三批做 V2 迁移

这三条数据主线来讲。
