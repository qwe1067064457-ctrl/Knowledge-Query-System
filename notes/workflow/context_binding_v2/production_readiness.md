# Production Readiness

## 当前状态

`Context Binding V2` 当前适合：

- 内部联调
- 灰度验证
- 继续支撑 `QA Runner V2` 演进

当前不建议：

- 直接生产放量

## 主要原因

### 1. relevant set 仍是规则第一版

当前规则覆盖：

- `第二点`
- `前两个`
- `这个说法`
- `那个结论`
- 简单 follow-up
- 简单 challenge

但还不能稳定覆盖：

- 用户换说法但不带显式 token
- 多轮语义漂移
- answer unit / assertion 字面不重合但语义接近
- 同 topic 多候选相似竞争

### 2. working memory writer 仍偏粗

当前写入 admission 主要依赖：

- 句子切分
- 判断词
- challenge hint
- task hint

还未达到生产级精度。

### 3. challenge 尚未完全统一

`ChallengePower` 仍未完全吃进 V2 relevant set / fallback contract。

### 4. retention / observability 仍不足

当前还缺：

- 长会话 retention 验证
- fallback / rewrite / clarification 分布观测
- relevant set 命中来源统计

## 正式结论

当前应把 `Context Binding V2` 定义为：

- 边界已稳定
- 实现为第一版
- 可灰度
- 未到生产放量标准
