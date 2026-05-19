# Intent V2 Migration

## 1. 为什么要做 V2

`V2` 不是简单换一套标签名，而是一次边界重构。

最核心的原因有三个：

1. `rule` 层做得太重
2. `evidence / resolver / control` 边界不够清楚
3. 旧口径已经开始影响后续执行流和数据治理

旧问题主要体现在：

- `resolver` 过早产出执行提示
- `task` 过早承诺执行方式
- `clarify` 过强裁决
- signal 同时承担多层职责
- 一些旧标签边界本来就脏，例如：
  - `system / capability / chat`
  - `unsupported / clarify`

## 2. V2 的核心目标

V2 的目标不是：

- 一口气推翻所有规则
- 立刻全量切到模型

V2 的目标是：

1. 收缩 understanding 层边界
2. 做 `rule-lite`
3. 为后续小模型接管留结构化接口
4. 用双轨迁移保护现有资产

## 3. V1 和 V2 的关系

### `V1`

定位：

- 历史稳定口径
- baseline
- teacher
- regression anchor

作用：

- 保留旧导出
- 保留旧评估
- 保留对比基线

### `V2`

定位：

- 新 understanding 语义
- 新 signal taxonomy
- 新 evidence / resolver 边界
- 新迁移评估线

作用：

- 接住新的结构设计
- 接住新的自动标注和质量闸门
- 为后续小模型准备更干净的输入

## 4. V2 改了什么

### 4.1 `evidence` 侧

从以前更扁平、职责容易混杂的 signal 组织方式，收缩到：

- `intent`
- `task`
- `context_fact`
- `safety`

### 4.2 `resolved` 侧

关键变化：

- `TaskTopology` 引入
- `mixed` 收紧
- `clarify_candidate`
- `ambiguity_state`
- 弱化旧执行型布尔字段

### 4.3 数据线

关键变化：

- `V2 auto` 自动标注打通
- `V1 vs V2 auto` 差异报告
- `quality gate`
- `V2` training export

## 5. 当前为什么要双轨

如果直接覆盖 `V1`，会立刻带来几个问题：

1. 旧模型训练口径漂移
2. 旧评估结果失去可比性
3. 很难判断新问题来自设计变化还是实现 bug

所以当前明确采用：

- `V1` 不覆盖
- `V2` 新起
- 新旧并行观测

## 6. 当前处于什么迁移阶段

当前阶段不是最终态，而是：

- understanding 主链已经部分 V2 化
- control 仍处于兼容承接阶段

可以理解成：

- 新结构已经进主链
- 旧字段影子还没有完全退掉

例如：

- `clarify_candidate / ambiguity_state` 已进入主链
- `needs_clarification` 还在兼容层保留

## 7. 当前 V2 最重要的设计方向

### 7.1 继续 `rule-lite`

rule 保留：

- `unsupported / safety`
- `system / scope_question`
- 粗分类
- 粗识别

rule 减少：

- 强裁决
- 细 task 终判
- 强执行承诺

### 7.2 把双角色 signal 拆开

目标不是继续允许：

- 一个 signal 同时落 `intent/context`

而是：

- 请求语义归请求语义
- 上下文事实归上下文事实

### 7.3 `clarify` 下沉

目标是：

- rule 不再最终裁决 clarify
- rule 只给出：
  - `clarify_candidate`
  - `possibly_ambiguous`
  - `needs_context_check`

最终是否澄清，由：

- 小模型
- 或主回答模型 / clarify workflow

## 8. V2 对项目的工程意义

V2 不是“为了多几个新字段”，而是为了：

1. 降低 rule 层维护成本
2. 让理解层更可解释
3. 让数据资产更可治理
4. 让后续模型接管更自然
5. 让面试讲项目时，能清晰讲出为什么架构要这样演进

## 9. 当前 V2 还没完全收完的地方

包括：

- 双角色 signal 的彻底退场
- `control v2` 正式收口
- 小模型真正承担中层理解
- `model_first_rule_guard` 的工程化模式切换

## 10. 一句话总结

`V2` 的本质不是“标签升级”，而是：

> 一次针对 understanding 主链职责边界、数据治理方式和后续模型接管路径的系统性收缩与迁移。
