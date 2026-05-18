# Intent SFT Split Policy

## 1. 文档定位

这份文档用于冻结 `intent` 小模型第一版的数据切分规则。

当前重点不是追求复杂数据管理，而是防止：

- 同一 seed 样本泄漏到不同 split
- 把 calibration 集和 held-out 混在一起
- 用 held-out 反向调参

---

## 2. 当前 split 角色

第一版只保留三类：

- `train`
- `dev`
- `heldout`

定义如下：

### 2.1 `train`

作用：

- 用于模型拟合

来源：

- 非冻结 gold
- 经过人工确认、适合训练的高质量样本

### 2.2 `dev`

作用：

- 选模型
- 调 epoch
- early stopping
- 比较不同超参和不同 baseline

来源：

- 从非冻结 gold 中切出
- 不能和 `train` 共享同一 seed 家族

### 2.3 `heldout`

作用：

- 最终验证
- 只在每轮训练完成后查看

来源：

- 当前固定使用 `frozen_heldout_v2`

---

## 3. 基本切分原则

### 3.1 同 seed 家族不得跨 split

这是第一优先级原则。

所谓同 seed 家族，包括：

- 同一个原始 query 的轻改写
- 同一个 query 的 near-miss
- 同一个 query 的 challenge / follow-up / mixed 派生变体

这些样本必须整体进入同一个 split。

### 3.2 冻结 held-out 不得参与任何调参

`frozen_heldout_v2`：

- 不得参与规则调优
- 不得参与训练
- 不得参与 dev 选型
- 不得用于手动迭代改 prompt/label 后再回看

它只用于最后的统一验证。

### 3.3 历史 calibration 集不等于 held-out

以下资产不能再当真正冻结 held-out：

- `heldout_judgment_soft_doubt_gold_v1`

原因：

- 它已经参与过规则收口
- 更适合作为历史 calibration / dev 辅助集

---

## 4. 当前建议切分来源

### 4.1 当前可训练主来源

- `backend_test/intent/test_data/gold/train/seed_query_20260514_gold_v1`
- `backend_test/intent/test_data/gold/train/seed_query_20260515_gold_v2`
- `backend_test/intent/test_data/gold/train/seed_query_20260516_gold_v1`
- `backend_test/intent/test_data/gold/train/seed_query_20260517_gold_v1`

### 4.2 当前第一版 dev

- `backend_test/intent/test_data/gold/dev/seed_query_20260515_gold_v1`

### 4.3 当前冻结 held-out

- `backend_test/intent/test_data/gold/frozen/frozen_heldout_v2`

### 4.4 当前暂不直接进入正式训练的来源

- `seed_query_20260514_campaign_v1`
- `heldout_judgment_soft_doubt_v1`
- `heldout_judgment_soft_doubt_gold_v1`
- 未复核的 query 派生草案

---

## 5. 当前切分策略

由于当前 gold 仍在增长，现阶段先冻结规则，再逐步调比例。

第一版建议：

- `train`
  - 占非冻结 gold 的大头
- `dev`
  - 保持一个完整 seed 家族级别的混合覆盖
- `heldout`
  - 固定使用冻结集

如果总 gold 仍明显偏少：

- 可以先做 very early probe
- 但不建议把 probe 成绩当正式模型结果

---

## 6. 去重规则

进入切分前，至少做三类去重：

1. 文本近重复
2. 同 seed 变体重复
3. 标签等价但只换少量语气词的机械重复

去重目标不是让样本“少”，而是避免模型靠模板记忆获高分。

---

## 7. split 元数据要求

每条样本至少要保留：

- `source_dataset`
- `source_query_id`
- `split`
- `label_tier`
- `is_heldout`

如果后面再导出新的训练文件，split 必须显式写进元数据，不能只靠目录推断。

---

## 8. 当前仍未完成的部分

这份 policy 现在只是 v1 草案，后面还需要进一步补：

- 具体 `train/dev` 样本清单
- 同 seed 族映射表
- 去重判定脚本

---

## 9. 当前结论

当前最重要的 split 原则只有三条：

1. 同 seed 家族不得跨 split
2. `frozen_heldout_v2` 永远冻结
3. 当前 gold 偏少时，probe 可以做，但不能把 probe 结果当正式结论
status: active-working
related_current_doc: notes/intent/test_data_generate/README.md
scope: sft split policy
