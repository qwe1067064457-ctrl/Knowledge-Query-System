# medicine 组知识库说明

这个目录用于保存医学相关知识库材料，原则上优先保存原始来源文档，并在可行时额外生成正文层。

## 当前规则

- 原文优先：优先保留原始 `html/pdf`
- 知识层并行：在原文之外，额外生成可检索的 `content.md` 或等价文本层
- 时间范围：默认优先收录 2022 年以后内容
- 抓不到原文或抓不到有效知识层时跳过

## 当前来源

- `documents/yiigle_cn/`：中文医学期刊页，保留原始网页，并优先从页面内嵌的全文 XML 抽取正文层
- `documents/open_access_pdf/`：官方开放获取医学文章，保留原始 PDF
- `documents/pmc_ftp_pdf/`：PMC Open Access Subset / FTP Service 官方清单里的原始 PDF

## 目录约定

- `metadata.json`：来源、标题、作者、日期、关键词等结构化元数据
- `source.html`：原始网页
- `source.pdf`：可下载时保存的原始 PDF
- `content.md`：面向检索和问答的正文层
