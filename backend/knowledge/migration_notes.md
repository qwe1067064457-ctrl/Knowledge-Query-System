# knowledge 目录迁移说明

## 当前定位

`backend/knowledge/` 已降级为迁移参考区，不再参与运行时知识检索扫描。

## 正式知识源位置

- `backend/storage/groups/general/knowledge/raw/`
- `backend/storage/groups/law/knowledge/raw/`
- `backend/storage/groups/medicine/knowledge/raw/`

## 历史目录用途

- `AI Knowledge/`
- `E-commerce Data/`
- `Financial Report Data/`
- `Safety Knowledge/`
- `groups/law/`
- `groups/medicine/`

这些目录仅用于：

- 一次性迁移输入
- 测试样本
- 目录结构参考

不再作为线上 runtime source roots。
