# 文献工作入口

当前目标：为从不完整、多来源材料重建虚构人物，寻找 **Personality Schema 与 Evidence Schema 的设计依据**。研究驱动产品设计；不开发真人心理测量工具。

先读 **[当前结论报告](output/schema-foundations/report.md)**，再看 **[字段依据表](organization/schema-field-matrix.md)** 和 **[下一步计划](plans/next-steps.md)**。

```text
literature/
  organization/                 文献整理：哪些文献支持哪些字段
    schema-field-matrix.md       当前核心：字段—依据—限制—验证
    reading-notes/              逐篇笔记；*-schema-basis.md 为当前主题
    legacy-catalog.md           旧39篇目录，保留作背景索引
  data/                         文献数据：可机器读取的研究记录
    schema-sources.json         当前23项核心来源，含阅读层级
    search-log.json             本轮问题、检索路径、纳入/排除规则
    source-manifest.json        下载结果、版本、指纹和访问限制
    archive-v1/                 上一轮39篇的历史编码数据
  output/                       可直接阅读的研究产出
    schema-foundations/         当前Schema依据报告（MD与HTML）
    archive-v1/                 上一轮宽范围报告与9张图，非当前主线
  plans/                        下一步计划、阅读顺序和完成标准
  sources/                      本地原文与抽取文本（不随Git分发）
  scripts/                      从研究记录重建报告的脚本
```

## 文件放置规则

1. 论文“讲了什么、哪里有局限”放 `organization/reading-notes/`；来源元数据放 `data/`。
2. 跨论文结论、图表、可打开的报告放 `output/`；待做事项放 `plans/`。
3. 一项设计若不能说明原文位置、推导过程和反例，不进入正式Schema。
4. P编号沿用旧目录；S01–S15为这轮新增核心来源。它们包括12篇研究论文与3项规范/文档，不混称15篇实证论文。
5. 旧报告是历史研究快照，其37篇定向核读＋2篇摘要背景状态不回写；P25/P26本轮补读进展以新笔记为准。

当前离线交互版：下载 `output/schema-foundations/index.html` 后用浏览器打开。重建：在仓库根目录运行 `python literature/scripts/build_schema_report.py`（需要 Python、markdown、matplotlib及中文字体）。
