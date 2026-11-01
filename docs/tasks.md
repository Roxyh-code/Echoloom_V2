# 当前任务板

更新日期：2026-10-31。状态仅取 TODO、IN_PROGRESS、DONE、DEFERRED。完成必须附可检查的交付物，不以“已经搜到”代替“已经读懂”。

| ID | 状态 | 下一步工作 | 完成证据／标准 |
| --- | --- | --- | --- |
| SETUP-01 | DONE | 初始化 Git、连接并推送 GitHub | `main` 已跟踪 `origin/main` |
| RES-01 | DONE | 扩大候选论文与作者网络 | [文献地图](research/literature-map.md)：39 篇候选、20 条引用关系 |
| PLAN-01 | DONE | 建立目录与总体研究计划 | [路线图](roadmap.md)、[研究计划](research/plan.md) 与各目录说明 |
| READ-01 | IN_PROGRESS | 精读 P27：人物模拟 | [笔记](research/papers/P27-character-simulation.md)：第一轮覆盖问题与方法；实验与附录待读 |
| READ-02 | TODO | P29：需求与工具综述 | 依模板完成笔记，指出我们服务的用户任务 |
| READ-03 | TODO | P06：CHIRON | 梳理档案生成、验证及证据缺口 |
| READ-04 | TODO | P08：PersoNet | 梳理情境与历史信息对特质判断的影响 |
| READ-05 | TODO | P07：BookWorm | 对照 description／analysis 与评价标准 |
| READ-06 | TODO | P02：FActScore | 定义原子主张与支持率，记录不能覆盖的错误 |
| READ-07 | TODO | P25：CAPS | 形成情境行为表示候选与反例 |
| READ-08 | TODO | P19：InCharacter | 判断访谈评估能否用于我们的人物模型 |
| SYN-01 | TODO | 汇总首批阅读的共识与分歧 | 在 `docs/design/` 写字段依据表；至少比较两种表示方案 |
| GAP-01 | TODO | 补搜多来源冲突与版本处理 | 记录查询、纳入理由、原文与实际引用关系 |
| DATA-01 | TODO | 建立原创多来源微型样例 | 来源清单、原文定位、预期冲突与人工标注 |
| SCHEMA-01 | TODO | Evidence／Personality Schema v0.1 | 合法／非法样例、未知和冲突表达、验证检查 |
| NOTE-01 | TODO | 1–2 页 Technical Concept Note | 问题、方法、替代方案、评估和开放问题 |
| CHAT-01 | TODO | 准备 Nicole 的讨论材料 | [准备文档](meetings/nicole-preparation.md) 中问题与材料齐全；是否联系由用户决定 |
| EXP-01 | TODO | 注册首个比较实验 | 基线、数据拆分、指标、成本预算和停止条件写在运行前 |
| CODE-01 | DEFERRED | 实现文本抽取流水线 | 待 Schema 与人工样例可用，避免过早固定接口 |
| UI-01 | DEFERRED | 档案审核原型 | 待流水线能导出带证据的档案 |
| DIALOG-01 | DEFERRED | 角色文字对话 | 待重建质量可衡量 |
| MEDIA-01 | DEFERRED | 视频、语音与视觉 | 文本核心验证后单独确定范围 |

## 接下来的三个动作

1. 完成 P27 Section 4–6、Limitations 和关键附录的阅读，检查实验设置与结论之间的距离。
2. 精读 P29 和 CHIRON；前者帮助确认用户任务，后者直接服务人物档案与验证设计。
3. 汇总首批字段假设，用一个原创反例手工演练；发现表示不足时再定向补文献。
