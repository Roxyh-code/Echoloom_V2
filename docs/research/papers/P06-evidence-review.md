# P06 — CHIRON: Rich Character Representations in Long-Form Narratives

阅读层级：全文定向核读。摘要、相关方法／数据／结果段落与定向附录；不等于逐页精读或复现。未复现。

- 原文：https://aclanthology.org/2024.findings-emnlp.499/
- 阅读版本：链接对应PDF；以SHA256固定
- PDF SHA256：65814643da59f393be704471fe3054c7f2615b257cea2fa065866e5c2530256b
- 定位：§3–6 Tables 2/3/6，PDF pp.3、5–7

## 方法与规模

问答生成人物档案，再通过专用蕴含模块过滤。529故事；1,403人物故事对；1,000条验证标注。

## 作者结果与证据边界

训练验证器精确率提高、召回率下降；档案用于遮名人物识别。

训练／测试标注量较小；最优类别子集有选择效应；不能把不支持都算编造。

## 对EchoLoom的分析

抽取与验证分开；同时报告错误和漏项。这是待验证的迁移建议，不是本文已完成的实验。

具体数字见[数值编码](../review/quantitative.json)，综合结论见[报告](../review/report.md)。
