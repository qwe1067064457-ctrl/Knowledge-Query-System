# Control Contract Migration Checklist

## 1. 当前目标

这份清单只服务于一件事：

- 把当前 `control` 从兼容过渡态迁到正式 contract

它不负责样本修复，也不负责 workflow 具体实现。

## 2. 兼容字段退出顺序

### 阶段 1：文档降级

- 把 `rewrite / decompose_query / use_planner / planning_level` 明确标成兼容字段
- 所有正式说明优先引用：
  - `route`
  - `handling_mode`
  - `capabilities`
  - `trace`

### 阶段 2：代码禁用新依赖

- 新代码不再以兼容字段作为主输入
- 新逻辑只允许消费：
  - `route`
  - `handling_mode`
  - `capabilities`
  - `trace`

### 阶段 3：workflow 入口迁移

- workflow 明确读取：
  - `route`
  - `handling_mode`
  - `capabilities`
  - `trace` 核心字段
- workflow 不再把兼容字段当成主入口

### 阶段 4：测试与评估迁移

- 将历史 `rag / direct / agent` 口径逐步迁到：
  - `qa`
  - `orchestrated`
  - `chat`
  - `reject`
- 将旧 mode 观察口径迁到：
  - `handling_mode`

### 阶段 5：正式删除

- 确认无主消费方依赖兼容字段后
- 再删除兼容导出

## 3. workflow 建议优先消费的 trace 字段

workflow 第一批建议只消费：

- `main_intent`
- `modifiers`
- `task_complexity`
- `task_shape`
- `task_topology`
- `context_dependency`
- `ambiguity_states`
- `missing_context_types`

暂时不建议 workflow 以这些字段做主判断：

- `decision_strength`
- `decision_source`
- `decision_reason`

它们更适合：

- 调试
- 解释
- 评估回放

## 4. 当前不要做的事

- 不要继续扩 `capabilities`
- 不要把 `clarify / challenge / compare / follow_up` 重新翻译成旧 planner 语义
- 不要用新增 rule 去硬补所有 route 灰区
- 不要让主回答模型在生成时临场决定 `route`

## 5. 后续应由 SFT/小模型承接的灰区

- `qa / orchestrated` 灰区
- `handling_mode` 组合灰区
- task 柔性边界
- ambiguity 强弱灰区

这些属于 understanding 收敛问题，而不是主回答模型的即时生成问题。
