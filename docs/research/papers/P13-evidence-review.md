# P13 — Enabling Large Language Models to Generate Text with Citations

阅读层级：全文定向核读。摘要、相关方法／数据／结果段落与定向附录；不等于逐页精读或复现。未复现。

- 原文：https://arxiv.org/abs/2305.14627
- 阅读版本：2305.14627v2
- PDF SHA256：ac8809fe3ca1d52a413f41ef97afd71c43924944d512c90477ec0c28f2ea3a4d
- 定位：§2–3，PDF pp.2–4

## 方法与规模

检索支持段落并生成带引用回答，分别评估引用和内容。ASQA、QAMPARI、ELI5三类任务。

## 作者结果与证据边界

引用支持与回答正确性是不同维度；仅后补引用并不可靠。

问答任务与人物分析不同；NLI仍有误判。

## 对EchoLoom的分析

来源标记不等于支持；证据应绑定主张。这是待验证的迁移建议，不是本文已完成的实验。

具体数字见[数值编码](../review/quantitative.json)，综合结论见[报告](../review/report.md)。
