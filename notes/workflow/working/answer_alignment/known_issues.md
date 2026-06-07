# Workflow Answer Alignment Known Issues

## K-001: answer side 对齐不应退回重做 workflow 主线

- 现象
  - 当前 goal 容易因为 `backend/graph` 的消费问题，倒逼回去重做 workflow 内部 contract
- 处理方式
  - 优先改消费侧读法
  - 只在 workflow 侧做最小必要补强

## K-002: graph 侧可能残留手工 summary dict 拼装

- 现象
  - `backend/graph/agent.py` 中仍可能存在手工拼装 `plan_summary / review_summary / evidence_summary`
- 处理方式
  - 优先改成消费 `summary_view()` / accessor
  - 只有兼容层才保留必要 dict fallback

## K-003: graph 侧剩余 owner field 直读不等于 answer side 未对齐

- 现象
  - `backend/graph/agent.py` 中仍会直接读取：
    - `payload.evidence_bundle.merged_evidence_items`
    - typed bundle 内部的结构字段
    - registry entry 组装所需的对象明细
- 处理方式
  - 如果这些读取属于 owner field / persistence 结构，而不是高频 summary 消费口，则按可接受范围保留
  - 当前阶段不为了消灭所有字段读取而扩大到 graph 主结构重写
