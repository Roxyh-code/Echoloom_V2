# P32 — Character-LLM: A Trainable Agent for Role-Playing

阅读层级：全文定向核读。摘要、相关方法／数据／结果段落与定向附录；不等于逐页精读或复现。未复现。

- 原文：https://aclanthology.org/2023.emnlp-main.814/
- 阅读版本：链接对应PDF；以SHA256固定
- PDF SHA256：f90514e50bcbbbcb69ab34d7b2e372c6c03af615bd9c91a43b7edec15a688dee
- 定位：§3–4 Tables 1–2，PDF pp.3–6

## 方法与规模

从人物简介合成经历并训练角色模型。9角色；857单轮+450多轮访谈问题。

## 作者结果与证据边界

训练角色可呈现特定经历与风格。

经历补全含合成细节；模型评价不证明这些细节属实。

## 对EchoLoom的分析

合成材料不得作为原文证据存回事实库。这是待验证的迁移建议，不是本文已完成的实验。

具体数字见[数值编码](../review/quantitative.json)，综合结论见[报告](../review/report.md)。
