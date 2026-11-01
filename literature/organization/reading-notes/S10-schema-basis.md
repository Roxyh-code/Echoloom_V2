# S10 · PROV-O: The PROV Ontology

原文：[PROV-O: The PROV Ontology](https://www.w3.org/TR/2013/REC-prov-o-20130430/)

类型：W3C规范；阅读：全文定向核读；未复现。

定位：§3.1 Starting Point；§3.2 Expanded Terms；§4 terms。

## 文献中的概念

区分实体、生成过程、责任主体和派生、修订等关系。

## 对Schema的设计启发（我们的推导）

source、span、extraction_run和review_action分别建对象，用派生边串起。

相关字段：evidence, time_version。

## 不能推出的结论

来源追踪不自动意味着支持关系或可信；不要求产品实现完整OWL，且alternateOf不能随意充当虚构世界版本标签。

全文访问情况见[来源清单](../../data/source-manifest.json)，候选字段及其验证条件见[字段依据表](../schema-field-matrix.md)。
