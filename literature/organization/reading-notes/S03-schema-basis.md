# S03 · CharacterGPT: A Persona Reconstruction Framework for Role-Playing Agents

原文：[CharacterGPT: A Persona Reconstruction Framework for Role-Playing Agents](https://aclanthology.org/2025.naacl-industry.24/)

类型：人物重建方法；阅读：全文定向核读；未复现。

定位：§2.1–2.3 PDF pp.2–3；Table 6 p.7；Limitations p.8。

## 文献中的概念

按章节增量组织八类人物信息，并可在叙事不同时间点形成档案。

## 对Schema的设计启发（我们的推导）

拆分特质、动机、背景、情绪、关系与变化；用chapter_cutoff防止未来信息泄漏。

相关字段：traits, states, goals, relationships, biography, time_version。

## 不能推出的结论

4名角色；八字段未获独立正式验证；语言风格证据不足；摘要抽取仍可能丢信息。CPT在这里主要是档案更新，不等同于参数微调。

全文访问情况见[来源清单](../../data/source-manifest.json)，候选字段及其验证条件见[字段依据表](../schema-field-matrix.md)。
