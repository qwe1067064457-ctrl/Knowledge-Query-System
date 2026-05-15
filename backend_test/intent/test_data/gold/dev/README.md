# Intent Dev Gold Datasets

`gold/dev/` 用于存放第一版小模型训练时可反复查看、可用于 early stopping 和超参选择的开发集。

约束：

- 这里的样本必须来自非冻结 gold。
- 同一 `seed` 家族不能同时出现在 `train/` 和 `dev/`。
- `dev/` 可以参与模型调参，但不能充当最终 benchmark。
- 真正最终验证仍然只看 `gold/frozen/`。

当前第一版 `dev`：

- `seed_query_20260515_gold_v1`
