# Legacy Intent Test Data

这里存放历史资产，目的是降噪而不是删除。

## 子目录

- `flat_batches/`
  - 早期平铺在 `test_data/` 根目录的单文件批次
- `old_campaigns/`
  - 旧版 campaign 或过渡性数据草案

## 使用建议

- 默认不要把这里当作当前训练或冻结评估的主入口
- 只有在追溯历史批次、兼容旧文档、或做对照时再进入这里
