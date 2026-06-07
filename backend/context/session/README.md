# Context Session

这里放 session 生命周期与兼容适配。

职责：

- session 创建、追加、归档、查询
- transcript 读写
- 会话级 `working memory` 的读写

`session working memory` 边界：

- 属于 session-scoped runtime state
- 用于执行连续性、中间结论保真、下一步执行提示
- 不等于 `daily_log`
- 不等于 `registry`
- 不承担长期记忆或跨轮对象注册职责
- 不承担 target resolution
- 不承担 `这个/那个` 指代解析
- 不承担 bound query 主判断

不负责：

- 上下文窗口裁剪
- registry object schema
- workflow 产物解释
