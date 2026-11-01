# P16 — Dialogue Natural Language Inference

阅读层级：全文定向核读。摘要、相关方法／数据／结果段落与定向附录；不等于逐页精读或复现。未复现。

- 原文：https://aclanthology.org/P19-1363/
- 阅读版本：链接对应PDF；以SHA256固定
- PDF SHA256：0090e43782ac4489fc15f8f8dbf38b65cbc0e50d9d4eb159de79092add4426b6
- 定位：§3–4 Tables 2–3，PDF pp.3–5

## 方法与规模

将persona与话语的一致性建模为蕴含／中立／矛盾。训练310,110对；gold test 12,376对。

## 作者结果与证据边界

NLI可用于重排候选话语以减少persona矛盾。

依赖PersonaChat与规则构造；逻辑矛盾不覆盖人格复杂性。

## 对EchoLoom的分析

语义冲突分类可参考，但要先处理版本和时间。这是待验证的迁移建议，不是本文已完成的实验。

具体数字见[数值编码](../review/quantitative.json)，综合结论见[报告](../review/report.md)。
