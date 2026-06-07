# Known Seams

## 当前判断

`QA Runner` 当前已经不需要再做大的结构性修改。

当前主要工作已从：

- 主链重构

转移到：

- 真实样本持续压测
- live 运行面观测
- 低成本高收益小修

## 当前仍成立的 seam

### 1. Live answer model latency / timeout

当前最主要的 seam 是：

- live answer model latency
- live answer model timeout
- provider / runtime availability

这类问题的表现是：

- 本地主链回归稳定
- full workflow 通过
- 但 live e2e 仍可能因为 answer model timeout 而 skip

### 2. Challenge 后续增强仍主要在 coverage

当前 `challenge` 的高收益增强点仍然是：

- evidence coverage
- existing evidence reuse quality

不是：

- 立即把主链升级成 fine-grained claim adjudication

### 3. Memory anchor hydration 仍需看真实收益

当前已经有最小接入点，但仍需要持续看：

- hydrate 命中率
- hydrate 后是否减少误 retrieval
- hydrate 后是否仍需补 challenge retrieval

## 当前不视为主要 blocker 的事项

以下内容当前不再视为主要结构性 blocker：

- `qa route` 定位
- `challenge` 是否独立 route
- `follow_up` 是否进入 `handling_mode`
- `QA Runner payload` 是否可消费

这些边界当前都已经相对稳定。

## 当前策略

如果没有新的真实 blocker，当前默认策略是：

1. 继续跑真实样本
2. 继续看 live 运行指标
3. 只做低成本高收益的小修
4. 把 seam 记录清楚，不急着全修
