# P21 — PersonaEval: Are LLM Evaluators Human Enough to Judge Role-Play?

阅读层级：全文定向核读。摘要、相关方法／数据／结果段落与定向附录；不等于逐页精读或复现。未复现。

- 原文：https://arxiv.org/abs/2508.10014
- 阅读版本：2508.10014v1
- PDF SHA256：ffce2c446bce0d5af387534728854da9679a30bb46f2b400340dfb900fbed5dd
- 定位：§4 Figure 3；§4.4，PDF pp.6、8

## 方法与规模

用自然对话进行角色身份识别，检验评估器能力。三个轨道；人类20名，每人50个模型困难案例。

## 作者结果与证据边界

最高模型全量识别68.8%；人类困难子集90.8%。

两成绩来自不同分布，不能作严格同条件差值；身份识别不等于全部评估。

## 对EchoLoom的分析

评分器也需要独立校验与困难反例。这是待验证的迁移建议，不是本文已完成的实验。

具体数字见[数值编码](../../data/archive-v1/quantitative.json)，综合结论见[报告](../../output/archive-v1/report.md)。
