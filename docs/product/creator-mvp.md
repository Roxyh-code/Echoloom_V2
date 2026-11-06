# EchoLoom Creator — 使用与更新

当前主方向：**Create characters. Discover their stories.** 为故事创作者提供角色驱动的互动创作工具。手机布局采用象牙白、石板灰、香槟金、鼠尾草绿和衬线标题；参考 `Zhguo903/Echoloom` 的设计语言。新增的车站和人物 SVG 为本项目绘制的演示素材。

## Windows：更新已有项目

先在前后端两个 PowerShell 窗口各按 `Ctrl+C`。下面在**项目根目录**执行，不是在 `web`：

```powershell
cd F:\课程\echoloom\Echoloom_V2
# 关闭服务后备份整个 work 文件夹；它包含数据库、图片和日历密钥。
Copy-Item .\work (".\work-backup-" + (Get-Date -Format "yyyyMMdd-HHmmss")) -Recurse
git pull --ff-only
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m uvicorn echoloom.api:app --host 127.0.0.1 --port 8000 --reload
```

保持后端窗口运行，另开一个 PowerShell 启动前端：

```powershell
cd F:\课程\echoloom\Echoloom_V2\web
npm.cmd ci
npm.cmd run dev
```

打开 **http://127.0.0.1:3000/creator**。根地址现在也会进入 Creator。用浏览器开发者工具切换到 393 × 852 可以预览手机布局；这是移动优先 Web 原型，不是安装包。真机访问需要单独配置可访问的同源地址，手机不能直接使用电脑的 `127.0.0.1`。

若尚未安装，请先按[首次安装说明](../mvp/README.md)完成 Python、虚拟环境、依赖和 `.env` 配置。此次没有增加第三方依赖。macOS/Linux 在根目录执行 `.venv/bin/alembic upgrade head`，然后按原启动说明运行两端。以上 PowerShell 命令经过语法检查，尚未经 Windows 真机验证。

## 已有数据

迁移 **0004** 增加 Creator 作品、请求恢复记录和角色归档标记，不清空旧表。保留原 `.env`、数据库路径、`work/portraits`、日历密钥和原账号。已有角色可直接用于新故事；原聊天、旧互动剧情与日历仍在 **http://127.0.0.1:3000/characters**，也可从 Creator 的 More options → Open companion 进入。

不要删除 `work`、重新建立空数据库或切换存储路径来更新。浏览器刷新不会删除已保存的服务端内容。输入中的草稿依赖本机浏览器存储，清理浏览器数据可能清除尚未提交的文字。备份文件含私人数据，请留在本地。

## 完整创作流程

1. **Create character**：描述人物，一次操作生成档案并自动生成头像。档案先保存；头像失败时单独重试，不重做人物。
2. 人物详情可 **Edit character**，修改动机、恐惧、秘密等；自然语言调整先预览差异再确认。头像可编辑、重新生成、查看候选和选择历史版本。人物可复制、归档。
3. **Start a story**：输入开场。选择 **Play a role**（你扮演一人）或 **Direct the cast**（导演两位 AI 人物）。不必先聊天、建 Project 或连接日历。可填写地点、时间、氛围、边界和世界规则；中途创建第二个人物会保留开场草稿。
4. 阅读器按片段呈现旁白、动作、对白。用 **Next / Show all** 阅读，用建议、自由指令、自己的台词或动作推动剧情。可手工编辑、重写、开始下一场戏。用户台词原样保留，AI 不应代写用户角色。
5. **Save storyline** 创建命名快照，之后继续不改变快照。**Try another version** 创建新路线，旧路线仍保留。历史片段编辑也会分叉；可以命名、切换、比较。
6. **Saved versions → Preview → Continue from here** 从保存点分出可编辑新路线，快照保持只读。Finish 会生成完成快照；继续写需另开路线。
7. **Story notes** 管理本路线的事实、知情人物和来源；重写来源会提示复核。母版人物修改不会自动改写旧作品，明确 Update characters 会创建新路线。
8. **Export story** 预览并下载当前路线、当前场景或保存版本的剧本／叙事文本；JSON 用于保留完整结构并导入独立副本。文本导出不包含内部提示和未选路线。叙事导出整理现有正文，不额外调用模型润色。

## 无密钥体验与真实 AI

首页 **Try The Last Train** 为清楚标记的 **Demo mode**：预置人物、插图和车站剧情，支持避而不谈、安静停顿、承认驻留邀请等路线。保存、编辑、分支、事实、导出和导入均真实落库。任意自由指令若不在示例范围，会提示需要 Live AI，并保留草稿。

自定义人物、自动头像、图片编辑和自由剧情使用现有服务端 `LLM_MODEL` / `LLM_API_KEY`、`IMAGE_MODEL` / `IMAGE_API_KEY`。模型必须支持所用接口并有可用额度。**不在前端填密钥。** 图像仍通过 Images API；此前可用的 `IMAGE_MODEL='gpt-image-1'` 可继续使用，是否有权限和收费由 API 账号决定。

没有用演示回复替代真实 AI 路径。云端回归使用隔离的测试替身，真实模型质量、耗时、费用和 Windows / iOS 真机体验仍须单独验证，见[验证记录](creator-validation.md)。

## 保存与限制

- 操作带请求 ID 和作品版本；重复提交复用结果，旧窗口冲突提示重新加载。停止等待可能只是取消浏览器等待，服务端仍可能完成原请求；重新进入可恢复结果。
- 内容保存在同一 SQLite 数据库；每部作品的正文是不可变片段图，分支与快照引用片段。事实、阅读位置和角色快照随路线保存。
- 已被作品引用的人物／头像不能直接删除；先归档，或处理引用作品。删除作品前导出备份；删除不能撤销。
- JSON 包含角色设定、秘密与全部路线，应视为私人草稿。**不打包头像二进制文件**；同一数据库可复用图片，异机或缺失图片会保留文字、显示占位形象。完整迁移仍需备份 `work`。
- 原型每部作品最多 1000 个片段、100 条路线、100 场景、100 组人物快照、100 保存点、500 事实；作品结构限约 4 MiB，导入限 5 MiB。不是无限长篇记忆或多人实时协作系统。
- 场景为两位参与者；长期设定一致性仍依赖上下文与人工复核，不承诺秘密永不泄露。请求日志用于去重与恢复，不是创作效果分析平台。

## 文件位置

- [完整 PRD](creator-mobile-mvp-prd.md)
- [定位与后续计划](README.md)
- [验证记录与待测项](creator-validation.md)
- 前端：`web/app/creator/`、`web/components/creator-app.tsx`
- 后端：`src/echoloom/creator_{schemas,domain,service}.py`
- 迁移：`alembic/versions/0004_creator.py`
