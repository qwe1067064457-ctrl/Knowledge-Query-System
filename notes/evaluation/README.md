# Evaluation Notes

`notes/evaluation/` 存放评测设计、交接与运行约定。

## 阅读顺序

1. `handoff/README.md`
2. `workflow_answer_eval_v0.md`
3. `rubrics/retrieval.md`
4. `rubrics/answer.md`
5. `operations/offline_eval.md`
6. `operations/online_sampling.md`

## 目录说明

- `handoff/`
  - 历史交接入口
- `rubrics/`
  - 评判标准文档
- `operations/`
  - 运行流程与协作约定

## 当前边界

- 第一阶段只做 `retrieval + answer`
- 不把 `compaction / memory extraction` 纳入首轮实现
- 不与 `monitoring` 混模块
- 当前评测链路固定为：`load cases -> rule layer -> model layer -> finalize layer -> report`
- 统一执行骨架已经收敛到 `backend/evaluation/core/`
