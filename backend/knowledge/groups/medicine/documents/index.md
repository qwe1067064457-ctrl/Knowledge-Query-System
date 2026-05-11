# 医学文献索引

这是 `medicine` 组的总入口，优先保存原始来源文档，并尽量补齐可检索的正文层。

## 已归档资料

- `documents/yiigle_cn/`：中文医学期刊样本，原始网页 + 全文 XML 优先的正文层
- `documents/open_access_pdf/`：开放获取医学样本，原始 PDF
- `documents/pmc_ftp_pdf/`：PMC FTP 官方 PDF 样本，原始 PDF

## 规则

- 原文优先，下载不到就跳过
- 原文之外，尽量生成 `content.md`
- 以 2022 年以后内容为主
