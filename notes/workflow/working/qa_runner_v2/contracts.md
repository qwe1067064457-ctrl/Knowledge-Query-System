# QA Runner V2 Contracts

## Retrieval Gate

`retrieval_gate.py` 是 policy 侧唯一额外拆出的文件。

对外应只暴露稳定决策：

- `must_retrieve`
- `prefer_retrieve`
- `can_answer_from_context`
- `needs_clarification_before_retrieval`
- `query_shape`
- `rewrite_needed`
- `memory_strategy`

内部 owner：

- `retrieval_gate_worker`

## Review 分层

`review_worker.py` 必须显式区分两层：

- `retrieval_quality_check(...)`
  - 粗 gate
  - 判断检索结果值不值得继续往后传
- `evidence_check(...)`
  - challenge / review 的任务层 adjudication
  - 判断当前证据是否足以支撑目标

## Session Working Memory

`session_working_memory.py` 只服务：

- 执行连续性
- 已确认中间结论
- 当前 rewritten query
- 当前未闭环问题
- 下一步执行提示

不服务：

- target resolution
- `这个/那个` 指代解析
- bound query 主判断

## Memory Anchor / Hydration

`memory_anchor.py` 返回：

- hit content
- `source_session_id`
- anchor / span key
- hydration availability

`context_hydrator.py` 负责：

- memory 命中后
- 在 challenge 或高需求场景
- 把周边历史对话上下文补给模型
