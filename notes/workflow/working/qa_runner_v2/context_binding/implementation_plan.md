# Context Binding Implementation Plan

## 目标

把 `context binding` 收口成：

- 按需触发
- relevant set 驱动
- 主大模型做最终 resolution / rewrite
- 结构化 fallback 收尾

## 代码 owner

- `workflow/powers/context_binding_power.py`
  - owner：整体 orchestrator
- `workflow/workers/binding_worker.py`
  - owner：规则筛选与 relevant set 压缩
- `memory_system/session_working_memory/resolver.py`
  - owner：从 short-term memory 取 active candidates
- `helpers/bound_query_prompt_helper.py`
  - owner：主大模型 JSON contract

## 实现顺序

### 1. relevant set 先落地

- recent conversation
- active working memory entries
- registry question objects
- optional memory anchors

### 2. 规则筛选链固定

- recent window
- type filter
- explicit pattern filter
- confidence / status filter
- simple score ranking

### 3. 主大模型做最终 resolution

输出：

- `resolved_target_ids`
- `rewritten_query`
- `confidence`
- `needs_clarification`
- `fallback_type`
- `reason`

### 4. fallback contract 固化

- `needs_clarification`
- `rewrite_without_target`
- `retrieve_on_raw_query`
- `answer_from_context_only`

### 5. QA 主链接入

- `qa_runner` 先调 `ContextBindingPower`
- retrieval / challenge 消费 binding 结果

## 当前第一版不做

- 不追求唯一 referent 恢复
- 不做 always-on history-aware retrieval
- 不让 working memory 当 referent truth source
- 不做小模型分层
