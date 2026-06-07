# Online Sampling

## 定义

第一阶段的线上评测是：

- 线上抽样
- 异步评测

不是同步阻塞主链路的在线打分。

## 流程

1. 从真实 trace 抽样
2. 组装统一 case
3. 异步跑规则 grader 与 LLM grader
4. 产出结果与报告
5. 把 `like/dislike` 作为排序信号

## 边界

- 不做 dashboard / alert
- 不做 SLA 监控
- 不把 `like/dislike` 当真值
