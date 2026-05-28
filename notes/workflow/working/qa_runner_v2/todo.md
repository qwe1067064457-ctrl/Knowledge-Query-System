# QA Runner V2 Todo

当前 focus：

- 把 QA / orchestrated 主链从 `capabilities/*` 回迁到 `power / worker`
- 把 retrieval / challenge / memory 的边界写死
- 建立 QA Runner V2 的独立知识目录

下一步：

1. 继续减少旧 `capabilities/*` 在主链中的残留调用
2. 继续观察 `retrieval_gate_worker` 当前轻策略 gate 的真实收益：
   - `knowledge_query`
   - `challenge_turn`
   - `memory_hit_needs_hydrate`
   - `context_answer_ok`
3. 继续观察 QA route 中 `memory anchor -> hydrate` 的真实命中率：
   - 什么时候摘要足够、不需要 hydrate
   - 什么时候 hydrate 后仍需要 retrieval
4. 继续观察 `qa_runner_e2e` 下 live LLM latency / timeout 与 fallback 行为：
   - binding 是否走了 LLM
   - retrieval 是否发生
   - challenge 是否触发 follow-up retrieval
   - 最终是否 fallback / `needs_clarification`
5. 如果后续继续增强 challenge，只从这三个入口切入：
   - evidence coverage
   - existing evidence reuse quality
   - fine-grained claim adjudication
6. 如果继续收 workflow 类型系统：
   - 保持对外 string contract
   - 内部继续优先使用 `Literal` / typed alias
   - 不把 `follow_up` 塞进 `handling_mode`

当前判断：

- `QA Runner` 主链已经进入“稳定 + 继续观测”阶段
- 当前不建议再开大改
- 后续默认策略：
  1. 继续跑真实样本
  2. 继续看 live 运行指标
  3. 只做低成本高收益的小修
  4. 把 seam 记录清楚，不急着全修
