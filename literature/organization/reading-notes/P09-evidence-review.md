# P09 — “Let Your Characters Tell Their Story”: A Dataset for Character-Centric Narrative Understanding

阅读层级：全文定向核读。摘要、相关方法／数据／结果段落与定向附录；不等于逐页精读或复现。未复现。

- 原文：https://arxiv.org/abs/2109.05438
- 阅读版本：2109.05438v1
- PDF SHA256：22563f29a9d3ec54af4b94dd4a4134f582f988a7d541e5f94019a0f03e08808c
- 定位：§3 Table 1，PDF p.3；后续识别与生成实验

## 方法与规模

从文学摘要识别人物并生成描述。过滤后9,499个人物样本；训练7,600／验证942／测试957。

## 作者结果与证据边界

将人物识别与人物描述作为独立任务。

用摘要简化了长书理解；参考描述可能含输入中没有的信息。

## 对EchoLoom的分析

分别评估人物归属和描述生成。这是待验证的迁移建议，不是本文已完成的实验。

具体数字见[数值编码](../../data/archive-v1/quantitative.json)，综合结论见[报告](../../output/archive-v1/report.md)。
