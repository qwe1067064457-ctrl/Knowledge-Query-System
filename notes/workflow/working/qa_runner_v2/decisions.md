# QA Runner V2 Decisions

## D-001: QA Runner V2 不继续写入 refinement

- 决策
  - 新知识统一落到 `notes/workflow/working/qa_runner_v2/`
- 理由
  - `refinement/` 更接近 workflow v1 完善期主目录
  - V2 再混进去会让专题边界继续变脏

## D-002: 不保留 capabilities 作为长期层

- 决策
  - 共享能力继续存在
  - 但通过 `power + worker` 表达
- 理由
  - `capabilities/` 会形成额外一层薄包装
  - 容易和 `power` 语义重复

## D-003: Retrieval 是共享 power，不归 QA 私有

- 决策
  - `retrieval_power` 同时服务 `qa` 和 `orchestrated`
- 理由
  - retrieval 是共享能力，不应该被误放进 QA 私有层

## D-004: Session working memory 不参与 bound query 主判断

- 决策
  - `working memory` 只保执行连续性
- 理由
  - 它不应替代最近对话、小候选集和 LLM rewrite / resolution

## D-005: retrieval_quality 粗，evidence_check 细

- 决策
  - `retrieval_quality` 负责检索层粗 gate
  - `evidence_check` 负责 challenge 任务层 adjudication
- 理由
  - 两者不能继续混成一个层
