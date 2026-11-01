# 原始来源（本地）

`pdf/`、`html/`、`text/` 保存已下载原文和文本提取，均被Git忽略；`../data/source-manifest.json` 保存本轮URL、文件指纹、访问情况。上一轮下载仍保留在项目本地 `work/papers/`，其清单归档于 `../data/archive-v1/source-manifest.json`。

下载成功不代表正文可读。HTML挑战页、正文抽取过短、纯扫描PDF和证书错误必须记录，不能计作全文阅读。某些来源通过网页工具核读全文，但本地没有可读副本；记录中会单列。原始论文链接见 `../data/schema-sources.json`。
