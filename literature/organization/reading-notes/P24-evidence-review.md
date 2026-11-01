# P24 — BOOKCOREF: Coreference Resolution at Book Scale

阅读层级：全文定向核读。摘要、相关方法／数据／结果段落与定向附录；不等于逐页精读或复现。未复现。

- 原文：https://aclanthology.org/2025.acl-long.1197/
- 阅读版本：链接对应PDF；以SHA256固定
- PDF SHA256：4ac510bf7dfc114e3fe2b300c0adaee233535fa42fb67cf76d2fe7c18d45103c
- 定位：§3 Tables 1–2；§4 Table 3，PDF pp.6–8

## 方法与规模

书籍级人物链接、过滤与分组共指扩展。silver 50书；gold 3书／约229k tokens。

## 作者结果与证据边界

pipeline gold CoNLL-F1为80.5。

gold仅3书；silver自动标签；书内共指不等于跨作品消歧。

## 对EchoLoom的分析

先验证人物归属，否则人格证据会串人。这是待验证的迁移建议，不是本文已完成的实验。

具体数字见[数值编码](../../data/archive-v1/quantitative.json)，综合结论见[报告](../../output/archive-v1/report.md)。
