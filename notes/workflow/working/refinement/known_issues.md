# Workflow Known Issues

## K-001: 仍有部分 retrieval 细节以 dict 方式被 challenge/review 假设

- 现象
  - retrieval 最终 bundle 已 typed 化很多，但 challenge/review 边仍有继续收口空间
- 处理方式
  - 优先补 `EvidenceBundle / RetrievalUnitResult` accessor
  - 新逻辑优先走 typed export，而不是手拆 `merged_evidence_items`

## K-002: summary ownership 已基本下沉，但残留读法还会回退到 summary dict

- 现象
  - 虽然已有 `summary_view()` 和 accessor，但有些逻辑仍会习惯性手翻 summary dict
- 处理方式
  - 新逻辑优先走 `summary_view()` 和 bundle accessor
  - 避免再新增 `review_summary[...]` 风格读法

## K-003: 当前不扩展 legacy main-chain 文件

- 现象
  - `memory_indexer.py`
  - `prompt_builder.py`
  - `session_manager.py`
  这些路径后续可能废弃或拔出
- 处理方式
  - 当前 workflow 完善阶段不继续把信息沉淀到这些旧主线文件

## K-004: 轮次计数必须外化

- 现象
  - 如果只在聊天里记轮次，压缩后容易丢
- 处理方式
  - `todo.md`
  - `compression_handoff.md`
  同步维护当前轮次和最近测试状态
