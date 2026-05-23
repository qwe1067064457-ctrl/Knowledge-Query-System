# Graph Prompt Builders

这里放 graph 侧的 prompt 组装逻辑。

职责：

- 主回答 prompt 装配
- classifier prompt 读取/组装
- workflow payload 到 prompt-facing 结构的投影

不负责：

- prompt 文本内容本身
- workflow schema 定义
- context 存储
