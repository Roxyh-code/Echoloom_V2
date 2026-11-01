# S13 · LongMemEval: Benchmarking Chat Assistants on Long-Term Interactive Memory

原文：[LongMemEval: Benchmarking Chat Assistants on Long-Term Interactive Memory](https://arxiv.org/abs/2410.10813v2)

类型：长时记忆评估；阅读：全文定向核读；未复现。

定位：§3.1–3.2 PDF p.4；Figure 1 p.3。

## 文献中的概念

区分信息抽取、跨会话推理、知识更新、时间推理和无法回答。

## 对Schema的设计启发（我们的推导）

memory保留时间与来源；query_time与valid_time分开；unknown是合法结果。

相关字段：beliefs_knowledge, time_version, conflicts。

## 不能推出的结论

个人助手记忆QA不是小说人格；仅引导字段可测试性，不据500题推出我们所需样本规模。

全文访问情况见[来源清单](../../data/source-manifest.json)，候选字段及其验证条件见[字段依据表](../schema-field-matrix.md)。
