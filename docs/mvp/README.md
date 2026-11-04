# EchoLoom MVP v0.1

本地单用户的虚构角色工作室：自然语言创建 → 编辑 → 对话 → 逐步调整。原有 `literature/` 研究资料保持原位。需求来源：[用户提供的 PRD](prd-v0.1.md)。

## 启动

需要 Python 3.12+、Node.js 20.9+（本环境验证 Python 3.12、Node 24），从仓库根目录执行：

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.lock
.venv/bin/python -m pip install --no-deps -e .
cp .env.example .env  # 仅在 .env 不存在时执行，保留已有配置
# 编辑 .env，配置自己的模型和 API 凭据
.venv/bin/alembic upgrade head
.venv/bin/uvicorn echoloom.api:app --host 127.0.0.1 --port 8000 --reload
```

Windows PowerShell 对应的后端命令（`uvloop` 已在锁定依赖中排除 Windows）：

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.lock
.\.venv\Scripts\python.exe -m pip install --no-deps -e .
# 仅在 .env 不存在时执行
Copy-Item .env.example .env
# 编辑 .env，配置模型和 API 凭据
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m uvicorn echoloom.api:app --host 127.0.0.1 --port 8000 --reload
```

Windows 启动命令尚未在 Windows 机器实测。以下前端命令适用于以上各系统。

另一个终端：

```bash
cd web
npm ci
npm run dev
```

浏览器打开 `http://127.0.0.1:3000/characters`。后端接口说明在 `http://127.0.0.1:8000/docs`。前端 `/api/*` 通过 Next.js 服务端转发到后端，浏览器不持有 API 密钥。可在启动前端前设置 `API_BASE_URL` 改变后端地址；生产构建的转发地址由**构建时**的该变量决定。

生产构建的本地验证：`cd web && npm run build && npm start`。这里只提供单用户原型，无登录或用户隔离；前后端均绑定回环地址。不要把它直接公开为多人服务。使用一个 Uvicorn worker；当前角色级互斥锁仅作用于同一进程。

## 模型配置

服务端 `.env`：

- `LLM_PROVIDER=openai`、`LLM_API_KEY`、`LLM_MODEL`：文字模型。
- `IMAGE_PROVIDER=openai`、`IMAGE_API_KEY`、`IMAGE_MODEL`：可选图片模型。图片密钥未填写时复用文字密钥。
- 模型名称无硬编码默认值，请选择账号实际可用的模型。文字模型须支持 Chat Completions 的 JSON mode、`max_completion_tokens`。图片模型须同时支持 Images generation/edit、`1024x1024` 和 base64 输出（GPT image 类型接口）；返回临时 URL 的旧模型不在当前适配器支持范围。
- 修改 `.env` 后重启后端。健康检查 `/api/health` 只报告配置是否存在、数据库是否迁移，不代表真实远端授权已通过。

运行环境没有配置 API 凭据时，模型操作返回清晰的 503；已有角色的读取、手动编辑、版本恢复和浏览历史仍可使用。**运行中的应用没有假 AI 模式**。不要将凭据写入 `NEXT_PUBLIC_*`、代码或测试文件；在云环境中通过安全的环境设置填写凭据，不要贴到聊天里。云端还需要允许 `api.openai.com` 的 HTTPS 出站访问。

使用 OpenAI 而非 PRD 首选的 Ideogram，是为了先用同一官方 SDK 覆盖生成和原图编辑；尚未进行付费的图片质量对比。`providers.py` 的 `TextProvider` 和 `ImageProvider` 是替换边界，业务层不依赖 SDK 响应格式。

实现时核对了 OpenAI 官方 SDK 的 [Chat Completions](https://github.com/openai/openai-python/blob/main/src/openai/resources/chat/completions/completions.py) 和 [Images](https://github.com/openai/openai-python/blob/main/src/openai/resources/images.py) 定义。模型的账户可用性仍需真实凭据验证。

## 已实现的流程

- 中文响应式角色库、创建页、字段编辑器和聊天页，包含等待、失败、重试与空状态。
- Pydantic 验证的角色数据；保留原始描述供核对，不强制虚构未知背景。生成补充内容尚未逐字段标注来源，用户应对照原始描述审阅。
- 稳定角色 ID、SQLite 持久化、多段对话、版本绑定的消息，刷新和重启后可以继续。
- 手动编辑无需模型调用；AI 精简字段修改先预览再确认；过期建议返回 409，防止覆盖其他页面的更新。
- 设定恢复创建新版本，保留旧版本、聊天与头像；更改设定后，下一次聊天使用最新设定。
- 原图生成、基于当前原图的编辑、候选预览、选用/恢复和丢弃。图片存到本地，不依赖临时远端 URL；头像与文字设定独立，不会因改图自动修改性格或外貌字段。
- 删除角色会级联删除设定、建议、对话、图片记录和对应本地图片。

## 数据和事务

代码在 `src/echoloom/`，前端在 `web/`，数据库迁移在 `alembic/`。数据库默认为 `work/echoloom.db`，图片为 `work/portraits/`，均已被 Git 忽略。备份应同时包含 SQLite 数据库和图片目录；应用停止后再复制，避免遗漏 WAL 中的写入。不要只备份 `.db` 而忽略正在使用的 WAL 文件。

人物设定是独立 JSON 结构，版本号保存在关系表中。并发编辑带 `expected_version`；聊天与设定、头像修改使用角色级互斥锁。聊天成功后一次事务保存完整问答；失败不写入半条对话。每条发送携带客户端 UUID，响应丢失后的同编号重试会返回已保存的消息，不再调用模型。此幂等保证适用于成功落库的请求；若进程在远端生成后、落库前崩溃，重试仍可能产生第二次远端费用。

设定/头像候选本身会持久保存；放弃设定建议不改人物，未接受的建议记录随角色删除。候选没有跨页“待办箱”；换页后可重新请求建议。丢弃头像会删除非当前且非其他版本父图的图片；作为父图的版本保持可访问。

## 成本、上下文与限制

配置见 `.env.example`：输入长度、输出预算、上下文预算、超时、每角色每小时图片请求数和图片体积上限。图片失败也计入预算，预算跨重启保留；图片不自动重试，避免重复付费。文字 SDK 最多重试一次，使用其退避机制。日志只记录操作类型、模型、耗时、成功状态和可用的 token 用量，不记录提示词、聊天正文或密钥。不根据不稳定的价格表伪造费用估算。

聊天始终携带当前设定，并读取最近最多 100 条消息；按 UTF-8 字节数保守估计 token，扣除输出和结构开销，保留连续的完整近期轮次。该策略会比精确分词更早截断，尤其是中文；旧消息仍全部保存在数据库。设定本身超预算时返回 422，而不是静默丢掉设定。未来可增加提供商分词器或摘要记忆。

图片请求使用同步 API + 前端等待状态，超时可配置；Next.js 转发等待上限为 240 秒。没有后台任务队列和跨刷新任务进度；生成期间请等待操作完成。模型本身不能保证编辑只改变指定像素，因此界面要求预览选用。没有局部蒙版编辑。

## 验证

```bash
# 仓库根目录；不调用付费 API
.venv/bin/python -m pytest -q

# 前端
cd web
npm run typecheck
npm run build
# 首次需要浏览器；已有 /usr/bin/chromium 会自动复用
npx playwright install chromium
npm run test:e2e
```

`requirements-dev.lock` 固定本环境验证过的后端/测试依赖，`web/package-lock.json` 固定前端依赖。Playwright 以临时数据库启动**仅测试用**的模拟 AI 后端（8001）和实际 Next.js（3001），测试结束即清理；绝不复用真实用户数据库，也不产生模型费用。可通过 `CHROMIUM_PATH` 指定系统浏览器。下载浏览器若受网络策略限制，可使用已安装的 Chromium，不需要关闭 TLS 校验。

覆盖创建与重启持久化、手动编辑、上下文裁剪、AI 修改预览/确认、过期建议冲突、设定恢复、聊天失败及并发重试去重、原图编辑、候选与版本恢复、角色归属、删除清理、图片请求预算和无凭据报错。浏览器覆盖完整旅程与响应丢失后的消息重试，包括手机宽度检查。

真实模型验收仍需凭据：用一个外貌明确、三项性格特征、特定背景与语气的角色，检查生成是否保留事实、聊天是否贴合设定、性格修改后新回复是否变化、原图编辑是否保留身份。自动化测试证明应用流程与适配器调用契约，不证明外部模型质量或账户权限。

## 当前边界

尚未做真实付费 API 验收、Ideogram/FLUX 适配器、严格的事实保持评测、流式输出、后台图片任务、语音/视频、向量记忆、账号、公共部署。认证、授权、限流、审核与多用户隔离应在公开部署前单独实现。研究路线仍保留在原 `literature/` 和 `docs/` 中，不影响本 MVP。
