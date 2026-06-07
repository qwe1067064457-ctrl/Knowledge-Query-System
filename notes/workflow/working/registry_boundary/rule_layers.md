# Rule Layers

当前 registry / workflow 外围边界采用 `rule-first`。

## Rule-Core

短期不计划模型化：

- token budget
- session prune
- registry 存储布局

## Rule-First

先规则，后面可模型辅助：

- workflow registry projection
- workflow registry consumer
- binding target filtering
- knowledge query heuristics

## Rule-to-Model

后续非常适合模型化：

- intent classification
- 跨轮引用解析
- registry extraction

## 训练数据潜在来源

- workflow payload 弱标签
- registry entries 弱标签
- transcript + review / binding 结果
- 未来人工修正样本

## 当前原则

- 先定 schema
- 再定 reuse rule
- 暂不接 slot model
