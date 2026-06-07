# Long-Term Memory Rubric

## 维度

- `should_write`
  - 该写入的长期记忆是否真的写入
- `should_not_write`
  - 不该写入的内容是否被正确拦住
- `type_correctness`
  - 写入类型是否符合预期
- `scope_correctness`
  - 写入 scope 是否正确
- `anchor_preservation`
  - 写入后是否保留可追溯历史锚点

## 原因标签

- `missed_write`
  - 预期应写入，但实际没有写入
- `unexpected_write`
  - 不应写入，但实际被写入
- `wrong_type`
  - 写入类型与预期不符
- `wrong_scope`
  - 写入 scope 与预期不符
- `missing_anchor`
  - 写入后没有保留可追溯锚点
