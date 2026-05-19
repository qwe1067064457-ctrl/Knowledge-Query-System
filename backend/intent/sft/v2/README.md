# Intent SFT V2

这条目录是 `intent` 小模型 SFT 的 `V2` 训练线。

它和现有 `backend/intent/sft/` 下的 `multisignal v1` 做物理隔离：

- `multisignal v1`
  - 只预测 6 个边界 signal
  - 目标是 `evidence.required_signals`
- `V2`
  - 面向 `intent / task / context / safety` 主骨架
  - 读取 `evaluation/intent/exports/v2/` 导出的 `V2 schema`

## 当前文件

- `v2_label_spaces.py`
  - 定义 `V2` 多头任务的标签空间
- `v2_data.py`
  - 从 `exports/v2` 或 `v2_auto_annotations` 读数据并导出 bundle
  - 支持通过 `split manifest` 重写 `dev / calibration / heldout`
- `v2_eval.py`
  - 多分类 / 多标签指标与阈值工具
- `v2_train_multitask.py`
  - `V2` 多头训练入口

## 当前定位

这是下一轮 `V2 understanding` 训练线的最小骨架，不回头扩规则职责，也不复用旧 `V1` 兼容语义作为训练目标。

当前默认 heads：

- `main_intent`
- `task_complexity`
- `task_shape`
- `task_topology`
- `modifiers`
- `context`
- `safety`

## 当前约束

- `V2 auto` 数据不等于人工复核 gold
- 当前仓库默认导出仍未冻结正式 `V2 calibration`
- 现在支持通过 `split manifest` 先构造 `calibration`，训练时可显式使用 `--threshold-source calibration`
- 若 bundle 没有 `calibration`，多标签 heads 仍默认在 `dev` 上选阈值
- 这只适合作为 `V2` 训练骨架，不适合作为最终评估协议
