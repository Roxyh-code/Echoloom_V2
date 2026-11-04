# EchoLoom

根据不完整、多来源文本重建虚构人物，并将人物判断关联到原文证据。

**MVP v0.1 已进入实现阶段：创建 → 编辑 → 对话 → 持续调整。** 本地应用的启动、配置和验证见 **[MVP 开发说明](docs/mvp/README.md)**，需求见 [PRD](docs/mvp/prd-v0.1.md)。使用 FastAPI + SQLite + Next.js，模型凭据由服务端配置。

原有研究线继续保留：为 Personality Schema 和 Evidence Schema 建立理论与方法依据。不把角色扮演成绩等同于重建正确性，也不开发真人心理测量工具；多文档抽取原型仍未实现。

## 先从这里看

- **[文献工作入口](literature/README.md)**：目录、当前报告、数据和下一步计划。
- **[Schema依据报告](literature/output/schema-foundations/report.md)**：围绕四条研究线的结论。
- **[字段依据表](literature/organization/schema-field-matrix.md)**：每项候选字段为什么需要、依据是什么、不能推出什么。
- **[下一步计划](literature/plans/next-steps.md)**：概念词典→原创样例→字段裁剪→Schema v0.1。

## 目录

```text
literature/      全部文献工作；整理、数据、产出、计划、原文与脚本
docs/            项目路线、任务、设计、评估及讨论准备
schemas/         研究与手工验证后再正式化的Schema
data/            后续原创角色和标注样例（区别于literature/data文献数据）
experiments/     后续方法比较与实验记录
src/echoloom/    MVP API、数据模型与 AI 适配器
web/            Next.js 角色工作室
alembic/        MVP 数据库迁移
tests/mvp/      MVP 业务与接口回归验证
```

旧39篇宽范围报告已归档到 `literature/output/archive-v1/`，不作为当前阅读顺序。项目总体框架见[路线图](docs/roadmap.md)与[任务板](docs/tasks.md)。本地 `work/` 为临时文件，`outputs/` 为可下载交付副本；Git内的规范报告位置为 `literature/output/`。下载的原始PDF与提取文本不上传Git。

## 最初目标

[最初的项目与研究讨论](https://chatgpt.com/share/6ae69724-ea88-83ea-9d19-9ab08b79b911)。当前优先目标按 `literature/plans/next-steps.md` 推进；视频、语音与完整平台在文本重建得到验证后另行安排。
