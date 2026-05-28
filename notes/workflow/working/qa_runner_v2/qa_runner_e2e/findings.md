# QA Runner E2E 发现

## 说明

这里记录 `QA Runner` 端到端验证里的稳定现象与风险点。

关注的不是 `Context Binding` 单点对错，而是：

- payload 是否可消费
- fallback 是否可接受
- challenge / answer side 是否被带偏
- 主回答模型是否放大噪音

## 当前观察框架

### Acceptable

- binding 较粗，但 payload 仍稳定
- live LLM 失败时，主链仍可保守 fallback
- 主回答模型没有明显放大错误绑定

### Blocker

- 错误绑定直接把主回答带偏
- clarification / fallback 被主回答模型忽略
- payload 已明确不确定，但主回答模型仍高自信乱答

## Round 1 Findings

### 1. `QA Runner payload` 这一层已经能带着上下文跑通

- 现象：
  - `E2E-R8`、`E2E-R4`、`E2E-R6` 都成功跑过：
    - `query + recent_messages + working_memory (+ registry_entries)`
    - `QaRouteRunner.run(...)`
    - `ExecutionPayload`
    - `answer prompt`
    - 主回答模型
- 根因判断：
  - 当前 workflow 主链已经能把 binding/review 信号真正投影到 answer prompt
- 是否需要修复：
  - 否

### 2. 主回答模型已经能消费 payload 的保守信号

- 现象：
  - `E2E-R6` 中，payload 明确给出 `needs_clarification`
  - 主回答模型没有直接高自信乱答，而是跟随“需要补更多上下文”的方向
- 根因判断：
  - `build_answer_result_projection_rules_from_workflow(payload)` 已发挥作用
- 是否需要修复：
  - 否

### 3. 当前最明显的端到端问题不是 binding 塌了，而是主回答模型输出出现 `<think>` 泄露

- 现象：
  - 3 条 live e2e 样本的主回答输出都带有明显 `<think>` 前缀
- 根因判断：
  - 当前主回答模型运行面没有把推理文本屏蔽干净
  - 这已经超出 `Context Binding` 单模块问题，属于 answer-model 层面的真实输出风险
- 是否需要修复：
  - 是，且优先级高
- 当前分级：
  - blocker

### 4. 端到端层面，`query_style` 偏粗目前不是首要矛盾

- 现象：
  - `E2E-R4` 里 `query_style` 仍然偏粗
  - 但 payload 和最终回答链并没有因此明显塌掉
- 根因判断：
  - 当前更大的风险已经转移到主回答模型输出形式
- 是否需要修复：
  - 暂不优先

## 当前结论

- `QA Runner payload` 主链目前是能跑通的
- `binding/review` 的保守信号已经能传给主回答模型
- 当前端到端最显著的新 blocker 是：
  - 主回答模型真实输出出现 `<think>` 泄露
- 所以下一步如果继续推进，优先级应转向：
  - 主回答模型输出约束
  - 而不是继续先抠 `Context Binding` 小规则

## Round 2 Findings

### 1. `related_only` existing evidence 现在不会被直接误判成 sufficient

- 现象：
  - 真实 challenge 问法 `那是模型的问题, 不是我们prompt问题?`
  - 如果 existing evidence 只是文本相关、没有 grounded ref
  - 当前会进入：
    - `retrieve_if_needed.reason = related_evidence_not_grounded`
    - 而不是直接 success
- 结论：
  - existing evidence reuse 边界已经更稳

### 2. targeted retrieval 已经能只围绕 coverage 缺口 target 发生

- 现象：
  - recovery 场景里只为 disputed target 构 support query
  - 没有把已覆盖 target 或 related-only evidence 的描述一起重搜
- 结论：
  - `related_only -> targeted retrieval` 这条链当前是稳定成立的

### 3. 当前 challenge coverage 的主要收益点已经从“找 target”转到“existing evidence reuse quality”

- 现象：
  - target 本身在真实 challenge case 里已经相对稳定
  - 更关键的是：
    - 已有 evidence 是否只是相关
    - 是否需要补 grounded evidence
- 结论：
  - 后续如果继续增强，优先级仍应保持：
    1. evidence coverage
    2. existing evidence reuse quality
    3. fine-grained claim adjudication
