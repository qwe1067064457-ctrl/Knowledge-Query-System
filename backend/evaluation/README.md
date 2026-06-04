# Evaluation

`backend/evaluation/` 现在按“`core` 通用执行框架 + topic 专题目录”两层组织。

## 顶层结构

- `core/`
  - 统一执行骨架：`load cases -> rule layer -> model layer -> finalize layer -> report`
- `workflow_answer/`
  - 第一阶段已落地的 Retrieval + Answer 评测专题
- `long_term_memory/`
  - 第二阶段长期记忆存储质量专题
- `working_memory/`
  - 第二阶段工作记忆连续性质量模板专题
- `compaction/`
  - 第二阶段压缩保真质量专题

## 阅读顺序

1. `backend/evaluation/core/runner.py`
2. `backend/evaluation/workflow_answer/README.md`
3. `backend/evaluation/workflow_answer/query_inputs/README.md`
4. `backend/evaluation/workflow_answer/rubrics/`
5. `backend/evaluation/long_term_memory/README.md`
6. `backend/evaluation/working_memory/README.md`
7. `backend/evaluation/compaction/README.md`

## 放置原则

- 通用接口与执行框架：放在 `backend/evaluation/core/`
- 评估脚本：放在对应专题目录下，例如 `backend/evaluation/workflow_answer/evaluate_workflow_answer.py`
- 评估输入：放在专题内的 `query_inputs/`
- 评估结果报告：放在专题内的 `reports/`
- 导出训练集或 benchmark 冻结物：放在专题内的 `exports/`
- rubric、reason tags、case schema：保留在各自专题目录内，不上提到 `core/`

## 当前状态

- `workflow_answer/` 已接入 `core.runner`
- `long_term_memory / compaction` 已接入同一模板并可跑最小闭环
- `working_memory` 已完成目录模板统一，业务实现待后续接入
- `core/` 只统一执行接口，不统一各专题维度定义
