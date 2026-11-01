# S09 · FactBank 1.0 Annotation Guidelines / Corpus Documentation

原文：[FactBank 1.0 Annotation Guidelines / Corpus Documentation](https://www.cs.brandeis.edu/~roser/pubs/fb_annotGuidelines.pdf)

类型：原始标注规范；阅读：网页全文指定章节核读；未复现。

定位：Guidelines §2.3、§3.3.2–3；2009 Corpus Documentation §5。

## 文献中的概念

事件的事实性判断与发言来源及嵌套转述相联系，并区分极性和确定程度。

## 对Schema的设计启发（我们的推导）

asserted_by、source_chain、polarity与modality不合并成置信分数。

相关字段：beliefs_knowledge, evidence。

## 不能推出的结论

报道语料规范；表示某人相信/声称的内容，不替我们判断该内容在故事中为真。

全文访问情况见[来源清单](../../data/source-manifest.json)，候选字段及其验证条件见[字段依据表](../schema-field-matrix.md)。
