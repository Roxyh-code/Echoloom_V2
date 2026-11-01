# P04 — Personalizing Dialogue Agents: I have a dog, do you have pets too?

阅读层级：全文定向核读。摘要、相关方法／数据／结果段落与定向附录；不等于逐页精读或复现。未复现。

- 原文：https://aclanthology.org/P18-1205/
- 阅读版本：链接对应PDF；以SHA256固定
- PDF SHA256：ae516847bf892b1e86983b9271ad635f093146341b7ebfc3ebb3e10608ad52f9
- 定位：§3，PDF pp.3–5

## 方法与规模

以给定短 persona 约束众包对话并训练模型。1,155 personas；10,981段对话／164,356轮话语。

## 作者结果与证据边界

显式档案支持更个性化的对话任务。

短自述、受限轮次；人物不是从多文档恢复；改写persona并非严格同义。

## 对EchoLoom的分析

采用档案基线，但避免只测词汇重复。这是待验证的迁移建议，不是本文已完成的实验。

具体数字见[数值编码](../../data/archive-v1/quantitative.json)，综合结论见[报告](../../output/archive-v1/report.md)。
