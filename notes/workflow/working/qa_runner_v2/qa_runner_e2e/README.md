# QA Runner E2E Working Notes

这个目录承接 `QA Runner` 端到端验证。

这里不再只看 `Context Binding` 单模块，而是看整条链：

1. `query + 上下文包`
2. `QaRouteRunner.run(...)`
3. `ExecutionPayload`
4. `workflow instructions -> answer prompt`
5. 主回答模型输出

当前策略：

- 主样本来自当前线程近 20 轮真实对话
- 不大规模补人工样本
- 只有出现明确 blocker 时，才补最小结构化样本

推荐阅读顺序：

1. `sample_set.md`
2. `execution_log.md`
3. `findings.md`
4. `../context_binding/pressure_testing/findings.md`
