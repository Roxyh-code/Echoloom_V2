# S12 · Integrating Conflicting Data: The Role of Source Dependence

原文：[Integrating Conflicting Data: The Role of Source Dependence](https://www.vldb.org/pvldb/vol2/vldb09-pvldb47.pdf)

类型：多来源融合方法；阅读：全文定向核读；未复现。

定位：§1–3 PDF pp.1–4，尤其§2 Assumptions。

## 文献中的概念

来源之间可能复制，重复支持不能视为独立投票。

## 对Schema的设计启发（我们的推导）

source的derived_from与dependence_group留入口；保留原始支持链。

相关字段：evidence, conflicts。

## 不能推出的结论

该方法寻求冲突值中的真实值，含独立性等假设；不同同人版本可以各自成立，不应直接套单一真值算法。

全文访问情况见[来源清单](../../data/source-manifest.json)，候选字段及其验证条件见[字段依据表](../schema-field-matrix.md)。
