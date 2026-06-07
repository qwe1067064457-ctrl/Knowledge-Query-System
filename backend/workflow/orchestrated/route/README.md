# route

## 职责

这个目录负责 `orchestrated` route 的顶层串接。

它负责把：

- binding frame
- decomposition
- planning
- execution layer
- challenge / review

串成一条完整主链，并把结果收口成 `ExecutionPayload`。

## 本质作用

它更本质地解决的问题，是把多个 owner 串成一条稳定可回归的编排主链，而不是把业务逻辑塞进单个 worker。

## 放什么

- route runner
- route 级收口逻辑

## 不放什么

- 不放 unit 级执行逻辑
- 不放 prompt 渲染逻辑
- 不放纯 contracts

## 与相邻层的边界

- 它消费 `binding / planning / execution_layer`
- 它产 `ExecutionPayload`
- 它不直接负责主回答模型最终 prompt
