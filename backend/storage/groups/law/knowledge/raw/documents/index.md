# 法律文献索引

这是 `law` 组的总入口，供 agent 先判断资料所在目录，再进入具体来源目录读取原始文档。

## 已归档资料

### 中国

- `documents/cn/flk/`：国家法律法规数据库原始文档，包含法规、司法解释及相关立法资料，保留 `pdf/docx` 原件
- `documents/cn/guiding_cases/`：最高人民法院指导性案例，保留原始 `html`
- `documents/cn/civillaw/`：中国民商法律网文章，保留原始 `html`

### 美国

- `documents/us/ecfr/`：eCFR 原始法规文本，按 section 拆分为 Markdown

## 待扩展方向

- `documents/cn/laws/`
- `documents/cn/regulations/`
- `documents/cn/judicial_interpretations/`
- `documents/cn/judgments/`

## 规则

- `documents/` 只保存原始文献或尽量接近原始来源的文档
- `domain_case` 仅保存从任务中沉淀出的可复用案例卡片和分析，不放大批量原文
