# P27 — Multi-Agent Based Character Simulation for Story Writing

阅读层级：全文定向核读。摘要、相关方法／数据／结果段落与定向附录；不等于逐页精读或复现。未复现。

- 原文：https://aclanthology.org/2025.in2writing-1.9/
- 阅读版本：链接对应PDF；以SHA256固定
- PDF SHA256：0c03ddf10908845f17a0ac1d2c8323714916a0094278882fc01eb74adf609d15
- 定位：§4–6；Appendix A，PDF pp.5–8、11

## 方法与规模

人物按时间模拟后再按叙述顺序重写。230 prompts中选择28；每对故事交换呈现顺序。

## 作者结果与证据边界

LLM偏好支持该方法；来源计划由参考故事反推。

无独立真人用户效果实验；非等成本消融；不能证明人格抽取有效。

## 对EchoLoom的分析

分离故事时间、呈现顺序和角色知识边界。这是待验证的迁移建议，不是本文已完成的实验。

具体数字见[数值编码](../../data/archive-v1/quantitative.json)，综合结论见[报告](../../output/archive-v1/report.md)。
