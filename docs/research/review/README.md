# 第一轮文献结论报告

- [直接阅读报告与图表](report.md)
- [离线交互报告](index.html)：下载后用浏览器打开；支持搜索、筛选、展开论文与下载数据，不依赖网络。
- [逐篇编码](coding.json)、[数值与分母](quantitative.json)、[编码规则](codebook.md)
- `figures/` 保存原创图表的 PNG 与 SVG。

范围：39 篇目的性候选；37 篇全文定向核读，2 篇摘要／理论背景。不是系统综述，不等于逐页精读或复现。完整限制见正文与编码规则。

## 重建

在仓库根目录运行 `python scripts/research/build_report.py`。需要 Python 3、matplotlib、markdown，以及支持中文的 Microsoft YaHei 字体（其他系统应在脚本中替换字体）。脚本不联网、不调用模型。

人工证据编码在 `coding.json`；定量图表的原值与绘制逻辑在构建脚本中维护，并同步导出 `quantitative.json`，每条保留论文 ID、原文定位、单位和适用范围。更新数字时应修改脚本并重新构建，避免单独改导出文件。

正文 `report.md` 是综合结论来源；构建后生成本目录 `index.html`、图表、39 篇 `../papers/Pxx-evidence-review.md` 与被 Git 忽略的 `outputs/literature-review/` 交付副本。后续逐页精读应更新人工编码和综合结论，不能仅改变阅读状态。

原始下载 PDF 和抽取文本留在本地 `work/`，未重新分发。逐篇记录保留公开原文链接、阅读版本与已取得 PDF 的 SHA256。
