# P07 — BookWorm: A Dataset for Character Description and Analysis

阅读层级：全文定向核读。摘要、相关方法／数据／结果段落与定向附录；不等于逐页精读或复现。未复现。

- 原文：https://aclanthology.org/2024.findings-emnlp.258/
- 阅读版本：链接对应PDF；以SHA256固定
- PDF SHA256：356e600b388f98e8917517f974722e4d337fbe73ca4b9c28e4ab18268a9d098a
- 定位：Tables 1–3，PDF pp.4、8；§5

## 方法与规模

长书人物描述／分析；比较检索、分层与微调。描述：324书／5,869样本；分析：133书／1,328样本。

## 作者结果与证据边界

检索普遍更有效；微调对描述与分析的收益不一致。

参考文本来自学习指南；存在数据污染与解释主观性；自动NLI分数不是人工准确率。

## 对EchoLoom的分析

事实描述与人格解释分开存储和评估。这是待验证的迁移建议，不是本文已完成的实验。

具体数字见[数值编码](../../data/archive-v1/quantitative.json)，综合结论见[报告](../../output/archive-v1/report.md)。
