# P01 — RoleLLM: Benchmarking, Eliciting, and Enhancing Role-Playing Abilities of Large Language Models

阅读层级：全文定向核读。摘要、相关方法／数据／结果段落与定向附录；不等于逐页精读或复现。未复现。

- 原文：https://aclanthology.org/2024.findings-acl.878/
- 阅读版本：链接对应PDF；以SHA256固定
- PDF SHA256：54e4015106249a51a1ba8168d67fbd8582cc827bc0ca4e7f8c27627fda03841a
- 定位：§3.2 Table 1–2；§4 Tables 3–5，PDF pp.5–6

## 方法与规模

基于档案、脚本知识和合成问答训练角色模型。100 个角色；168,093 条指令（包含不同子集）。

## 作者结果与证据边界

质量抽查中最严格一层为77%；训练角色模型可优于若干基线。

数据大部分经模型生成；角色扮演和原文忠实抽取是不同任务。

## 对EchoLoom的分析

知识、风格、人格的评价应分开。这是待验证的迁移建议，不是本文已完成的实验。

具体数字见[数值编码](../review/quantitative.json)，综合结论见[报告](../review/report.md)。
