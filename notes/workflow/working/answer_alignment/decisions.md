# Workflow Answer Alignment Decisions

## D-001: answer side 对齐阶段单独隔离外部记忆

- 决策
  - 当前 goal 的活跃状态单独写入 `notes/workflow/working/answer_alignment/`
- 理由
  - 避免与前两个 workflow goal 的阶段状态混写
  - 让 answer side 对齐阶段的压缩与续接可独立进行
- 影响范围
  - 当前 goal 的 `todo.md`
  - `compression_handoff.md`
  - 阶段性 decision / known issues

## D-002: answer side 优先对齐高频 summary/accessor 消费口，不为清空所有 graph 侧 dict 读法而扩大范围

- 决策
  - 当前阶段优先收 `backend/graph/agent.py` 里的高频 workflow summary 消费口
  - 不为了继续清理所有 graph 侧字段读取，而扩大到新的 graph 主结构重构
- 理由
  - 当前 goal 的核心是：
    - answer side 优先消费 `summary_view()` / accessor
    - workflow -> answer side 的 ownership 更清楚
  - 经审计后，剩余 graph 侧读法多数属于：
    - owner field 直接读取
    - registry entry 持久化所需的结构字段
    - 非 answer 主消费口
- 影响范围
  - `backend/graph/agent.py`
  - answer instruction 构建
  - execution summary metadata 组装
  - registry entry 构建
