# QA Runner V2 Known Issues

- `capabilities/` 目录目前仍存在
  - 现阶段可视为兼容桥接残留
  - 不应继续往里新增主实现

- `context_binding_power` 仍保留内部短程 state snapshot 逻辑
  - 但这不等于 session working memory
  - 不应再把它写成 session owner 口径

- challenge 仍允许 follow-up retrieval
  - 这是受控补检索
  - 不能让它重新演化成“主链没有 retrieval，只靠 challenge 补查”

- `daily_log / domain_case` 的 anchor / hydrate 已建最小链路
  - 但后续仍需评估命中后补水成本与收益
