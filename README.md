# EchoLoom

从多来源文本中重建虚构人物的人格模型，并将每项判断关联到原文证据。

## 当前阶段

研究与问题定义。已建立 39 篇候选文献地图，正在精读第一篇 P27；尚未实现抽取原型。Python、Pydantic、SQLite 是原型候选技术，待研究和小样本验证后确定。

当前闭环：多份文本 → 人物与原文证据 → 情境化人格档案 → 用户审核 → 质量评估。

## 从哪里开始

- [总体路线图](docs/roadmap.md)：所有阶段、依赖与完成标准。
- [当前任务板](docs/tasks.md)：下一步具体工作与真实状态。
- [研究计划](docs/research/plan.md)：研究问题、方法和交付物。
- [39 篇文献地图](docs/research/literature-map.md)：候选论文、作者网络和已核实引用。
- [精读队列](docs/research/reading-queue.md)：顺序、阅读问题和进度。
- [第一篇精读](docs/research/papers/P27-character-simulation.md)：问题、方法与待核实事项。

## 目录

```text
docs/
  roadmap.md                  总体工作框架
  tasks.md                    当前任务与完成记录
  research/                   研究计划、文献地图、精读笔记
  design/                     概念、Schema 假设与技术方案
  evaluation/                 标注与评估协议
  decisions/                  设计决策及依据
  meetings/                   专家讨论准备与反馈
schemas/                      后续 JSON Schema 与合法示例
data/                         原创样例与数据说明
experiments/                  实验协议、配置与结果记录
src/echoloom/                 后续 Python 原型
tests/                        后续数据约束与行为回归测试
```

各目录的 README 说明用途与进入条件；当前不是已可运行的应用。`work/`、`outputs/` 是本地临时／交付副本目录，不纳入 Git。视频、语音、Avatar 和完整平台在文本重建验证后再安排。

## 计划来源

[EchoLoom 开发计划与研究讨论](https://chatgpt.com/share/6ae69724-ea88-83ea-9d19-9ab08b79b911)
