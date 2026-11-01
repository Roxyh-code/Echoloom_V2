# P02 — FActScore: Fine-grained Atomic Evaluation of Factual Precision in Long Form Text Generation

阅读层级：全文定向核读。摘要、相关方法／数据／结果段落与定向附录；不等于逐页精读或复现。未复现。

- 原文：https://aclanthology.org/2023.emnlp-main.741/
- 阅读版本：链接对应PDF；以SHA256固定
- PDF SHA256：8486fe22a15aaf3fe2e1d7043d169000600205dde9c601c9fd31c0dd6f7380e9
- 定位：§3.3–3.4 Table 1，PDF p.4

## 方法与规模

将长文本分解成原子事实并相对知识源判断支持。183 位人物的传记生成；三类生成系统。

## 作者结果与证据边界

三系统 FActScore 为42.5、58.3、71.5。

主要是客观传记与维基百科；不直接测解释性人格主张；事实支持不包含遗漏。

## 对EchoLoom的分析

先拆主张，再验证；同时另测覆盖。这是待验证的迁移建议，不是本文已完成的实验。

具体数字见[数值编码](../review/quantitative.json)，综合结论见[报告](../review/report.md)。
