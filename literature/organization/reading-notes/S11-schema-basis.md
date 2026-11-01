# S11 · TimeBank 1.2 Documentation / TimeML

原文：[TimeBank 1.2 Documentation / TimeML](https://timeml.github.io/site/timebank/documentation-1.2.html)

类型：原始标注规范；阅读：全文定向核读；未复现。

定位：Overview of TimeML：TIMEX3、EVENT、LINK。

## 文献中的概念

分别表示事件、时间表达、锚定和相对时间关系。

## 对Schema的设计启发（我们的推导）

story_time与文本位置、录入时间分开；不清楚日期时保留before/after和未知。

相关字段：time_version, states。

## 不能推出的结论

主要面向新闻；复杂倒叙、平行世界和用户版本需要项目扩展，不能强制绝对日期。

全文访问情况见[来源清单](../../data/source-manifest.json)，候选字段及其验证条件见[字段依据表](../schema-field-matrix.md)。
