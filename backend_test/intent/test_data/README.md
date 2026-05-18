# Intent Test Data

`backend_test/intent/test_data/` 现在按数据角色分区，而不是按时间或脚手架来源平铺。

## 目录约定

- `legacy/`
  - 历史平铺数据与旧 campaign
  - 保留参考价值，但不作为当前训练或评估主入口
- `campaign/`
  - 从 `seed` 派生出来的对抗草案和增强池
  - 适合压测、找 badcase、继续提升成 `gold` 或 `silver`
- `gold/`
  - 当前最重要的标注区
  - `train/`：高质量 `gold` 训练样本
    - `seed_query_20260518_gold_v1/`：本轮 multi-signal SFT v1 的训练回补，重点补 `needs_clarification`、`complex` 和 `follow_up/needs_clarification` 对照组
  - `silver/`：由 `auto-uplift` 批量生成的 `silver` 训练样本
  - `dev/`：从非冻结高质量样本中切出的开发集
  - `calibration/`：参与过调优的开发校准集
    - `multisignal_20260517_v2/`：覆盖 6 个 signal 的 calibration v2，正例与 hard negative 混放，用于阈值调优
  - `frozen/`：真正冻结的 benchmark / held-out
    - `frozen_heldout_v2/`：历史冻结集，保留不动
    - `frozen_heldout_v3/`：补齐 6 个 multi-signal 边界信号覆盖的新冻结集
- `experiments/`
  - 专项实验、用户批次、脚手架 smoke




## 当前使用建议

如果你的目标是：

- 继续补训练集：先看 `gold/train/` 和 `gold/silver/`
- 做开发验证：先看 `gold/dev/`
- 做阈值调优：先看 `gold/calibration/multisignal_20260517_v2/`
- 做最终验证：先看 `gold/frozen/`
- 找待提升样本：先看 `campaign/`
- 查历史资产：看 `legacy/`
- 看专项批次：看 `experiments/`

## 说明

- `gold/frozen/` 下的数据不得参与规则调优
- `campaign/` 下的数据默认不直接进入最终 benchmark
- `silver` 可以进入训练，但默认权重低于 `gold`
- `legacy/` 下的数据保留，但不再作为主入口
