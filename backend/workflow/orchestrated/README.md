# orchestrated

## 职责

这个目录承接 `workflow` 里专属于 `orchestrated` route 的 owner。

它统一组织：

- `binding`
- `planning`
- `execution_layer`
- `answer_layer`
- `route`

## 本质作用

它更本质地解决的问题，不是“多放几个 worker”，而是把一个复杂 query 从单轮回答请求提升为：

- 可编排
- 可分层
- 可让后续层稳定消费

的执行链。

## 放什么

- 只放 `orchestrated` 专属的编排 owner
- 只放和多步执行图强相关的实现与说明

## 不放什么

- 不放 QA route 的共享逻辑
- 不放最终主回答模型的统一 prompt render
- 不放通用的 retrieval / review / policy owner

## 与相邻层的边界

- 上游：
  - `workflow policy` 决定是否进入 `orchestrated`
- 下游：
  - shared prompt mapping 把 answer-facing 结果渲染成主模型可消费的文本 prompt
