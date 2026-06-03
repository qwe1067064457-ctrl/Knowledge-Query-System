# Graders

这里放 Workflow + Answer 主题的 grader 组件。

## 文件说明

- `retrieval_rules.py`
  - retrieval 规则 grader、硬门槛、综合分计算
- `answer_rules.py`
  - answer 规则 grader、硬门槛、综合分计算
- `retrieval_llm_grader.py`
  - retrieval 语义维度的 prompt 与响应校验
- `answer_llm_grader.py`
  - answer 语义维度的 prompt 与响应校验
- `adjudication_router.py`
  - 决定是否需要人工复核

## 分工

- 规则 grader
  - 结构检查
  - 缺字段、空证据、空回答
  - 综合分聚合
  - hard cap
- LLM grader
  - 相关性、充分性、groundedness 等主观维度
  - 每个维度单独 prompt
- 人工复核
  - 低置信度
  - 用户反馈与模型评分冲突
  - 重要 bad case
