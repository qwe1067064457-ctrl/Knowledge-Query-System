# Multi-Signal SFT v1

这条工作线只做 `evidence.required_signals` 的边界信号预测，不做：

- `main_intent`
- `resolved`
- `control`
- 最终 rule decision

## v1 标签范围

第一版只保留 6 个边界 signals：

- `soft_doubt`
- `follow_up`
- `needs_clarification`
- `ask_source`
- `multi_question`
- `complex`

这些标签来自现有四层 gold/silver 数据里的 `gold.evidence.required_signals`。

## 数据来源

- `train`
  - `backend_test/intent/test_data/gold/train/*`
  - `backend_test/intent/test_data/gold/silver/*`
- `dev`
  - `backend_test/intent/test_data/gold/dev/seed_query_20260517_gold_v2`
- `calibration`
  - `backend_test/intent/test_data/gold/calibration/heldout_judgment_soft_doubt_gold_v1`
- `heldout`
  - `backend_test/intent/test_data/gold/frozen/frozen_heldout_v3`

约束：

- `frozen` 不参与训练
- `frozen` 不参与阈值选择
- `campaign` 不进入第一版正式训练

## 训练口径

- 输入默认 `query-only`
- 模型：`hfl/chinese-macbert-base`
- 训练方式：全参数微调 baseline
- 训练损失：多标签 BCE
- 样本权重：
  - `gold = 1.0`
  - `silver = 0.4`

`dev` 只用于：

- 选 best checkpoint
- 选 epoch
- 观察过拟合

`calibration` 只用于：

- 为每个 signal 选择阈值

## 运行方式

导出训练 bundle：

```bash
python3 backend/intent/sft/data.py /tmp/intent_sft_multisignal_bundle
```

做 dry-run 校验：

```bash
python3 backend/intent/sft/train.py /tmp/intent_sft_multisignal_bundle /tmp/intent_sft_multisignal_run --dry-run
```

正式训练：

```bash
python3 backend/intent/sft/train.py /tmp/intent_sft_multisignal_bundle /tmp/intent_sft_multisignal_run
```

## 输出文件

- `config.json`
  - 训练配置
- `dataset_summary.json`
  - split 大小与各 signal 覆盖
- `thresholds.json`
  - calibration 选出的逐信号阈值
- `metrics.json`
  - per-signal 与 overall 指标
- `*_errors.jsonl`
  - 各 split 错误样本
- `README.md`
  - 当前 run 摘要
- `model/`
  - 训练后的模型文件

## 当前限制

当前 split 覆盖已经更新到：

- `dev`
  - `soft_doubt=4`
  - `follow_up=4`
  - `needs_clarification=4`
  - `ask_source=4`
  - `multi_question=4`
  - `complex=8`
- `heldout_v3`
  - 6 个边界 signal 均为 `5`

现状意味着：

- 这条线现在适合做 baseline
- 但 `calibration` 目前仍然主要覆盖 `soft_doubt`
- 对其余 5 个 signal 的阈值稳定性，仍需单独扩充 calibration 集再做正式比较
