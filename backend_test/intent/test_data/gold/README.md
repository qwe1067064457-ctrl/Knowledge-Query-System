# Intent Labeled Datasets

这里存放当前 `intent` 模块的结构化四层样本，已经按训练角色分层。

## 子目录

- `train/`
  - 高质量 `gold` 训练样本
  - 默认进入训练导出
- `silver/`
  - 由 `campaign` 通过 `auto-uplift` 批量提升出来的 `silver` 训练样本
  - 默认进入训练导出，但标签权重应低于 `gold`
- `dev/`
  - 从非冻结高质量样本中切出的开发集
  - 用于 early stopping、超参选择和 baseline 比较
- `calibration/`
  - 参与过规则调优的开发校准集
  - 适合开发分析，不适合作为最终 benchmark
- `frozen/`
  - 真正冻结的 benchmark / held-out
  - 不得参与规则调优或训练回填

## 使用建议

- 训练导出默认读取 `train/` 和 `silver/`
- 开发验证优先读取 `dev/`
- 最终验证只读取 `frozen/`
- 历史开发校准只读取 `calibration/`
- `seed query` 只作为原料和增强输入，不直接进入最终 benchmark

## 当前原则

- `gold`：少而精，承担高权重训练、dev 和 frozen
- `silver`：批量扩量，承担主训练量
- `frozen`：只评估，不反向修规则
