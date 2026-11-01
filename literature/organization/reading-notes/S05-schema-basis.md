# S05 · ATOMIC: An Atlas of Machine Commonsense for If-Then Reasoning

原文：[ATOMIC: An Atlas of Machine Commonsense for If-Then Reasoning](https://arxiv.org/abs/1811.00146)

类型：常识知识表示；阅读：全文定向核读；未复现。

定位：§2、Table 1 PDF pp.2–3。

## 文献中的概念

九种关系区分事件前提、意图、后果、情绪及行动者与他人。

## 对Schema的设计启发（我们的推导）

inferences保留关系类型、行动者/受影响者及候选解释；生成常识只进入hypothesis。

相关字段：states, goals, behavior_patterns, evidence。

## 不能推出的结论

常见的可能解释不能作为某个角色的事实证据；xAttr也不是稳定特质的证明。

全文访问情况见[来源清单](../../data/source-manifest.json)，候选字段及其验证条件见[字段依据表](../schema-field-matrix.md)。
