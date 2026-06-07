## 职责
- 放 execution unit 可直接调用的 worker。

## 本质作用
- 把 unit 内可复用能力沉到稳定的 execution-callable 层，避免 executor 直接依赖 power。

