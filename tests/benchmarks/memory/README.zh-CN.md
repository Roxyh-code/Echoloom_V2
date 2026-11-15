# Echoloom 记忆 A/B 自动测试

该目录属于原来的 **Echoloom_V2 项目**，不需要创建第二个项目。测试内容均为虚构人物和虚构对话。**程序调用你已启动的本地后端，会产生真实的 OpenAI API 费用**，并在当前数据库创建测试角色和场景；建议使用独立测试数据库。

## 1. 从 GitHub 更新原来的项目

在 PowerShell 中进入 **你 iCloud Drive 里原来的 Echoloom_V2 文件夹**：

```powershell
git status
git pull --ff-only origin main
```

如果 `git status` 显示有本地未提交修改，请先提交/备份；不要使用 `git reset --hard` 强制清理。目录中的 `.env` 和 `work/` 不会因正常 `git pull` 被主动覆盖，但应先备份重要数据，并避免在应用运行时直接移动/复制 SQLite 数据库文件。

脚本路径：`tests\benchmarks\memory\`。不需要单独下载 ZIP。

## 2. 启动已有后端并设置账号

按照原项目 `docs/mvp/README.md` 启动 API（默认 `http://127.0.0.1:8000`）。确认数据库迁移已完成，`.env` 里的文本模型可以正常使用。

如果已创建本地账号，在**同一个 PowerShell 窗口**运行：

```powershell
$env:ECHOLOOM_TEST_USERNAME = '你的Echoloom本地账号'
$env:ECHOLOOM_TEST_PASSWORD = Read-Host 'Echoloom login password'
```

请勿上传 `.env`、API Key 或密码。

## 3. Character Chat：同会话 vs 新会话

Character Chat 按 Conversation 保存近期上下文，**没有接入 Rehearsal 的 Mem0**。下面是对话机制的诊断性测试，不是 Mem0 A/B：

```powershell
py -3.12 .\tests\benchmarks\memory\run_benchmark.py --mode chat --label chat_baseline
```

自动发送六组模拟聊天（总计 12 条用户输入），再在同会话、新会话分别回答 15 道问题；所有提问会产生真实模型调用。可添加 `--filler-turns 60` 测长对话遗忘（增加费用）。

## 4. Rehearsal：真正的 Mem0 A/B

两组使用同一套脚本、同一个 LLM 模型、相同配置和新建测试场景。**每次改 `.env` 后都要重启后端**。

### A：关闭 Mem0

后端 `.env`：`MEMORY_ENABLED=false`，重启后端，然后在原项目根目录执行：

```powershell
py -3.12 .\tests\benchmarks\memory\run_benchmark.py --mode rehearsal --label memory_off
```

### B：开启 Mem0

先按照 `docs/mvp/rehearsal-memory.md` 安装可选依赖；后端 `.env`：`MEMORY_ENABLED=true`，按原文设置 `MEMORY_*` 参数并重启，然后执行：

```powershell
py -3.12 .\tests\benchmarks\memory\run_benchmark.py --mode rehearsal --label memory_on
```

**注意**：`GET /api/health` 不暴露内存开关值。需要你自己核对服务端实际配置。Rehearsal 只索引正式提交并含 `known_by` 的状态变化；这些内容必须由模型实际生成。模型可能没有输出有效来源，且索引是异步的。因此 B 组出现 `empty`、`partial`、`pending`、`degraded` 等状态时不能直接归咎于记忆质量。

## 5. 比较输出

```powershell
py -3.12 .\tests\benchmarks\memory\compare_runs.py .\tests\benchmarks\memory\benchmark_results\memory_off .\tests\benchmarks\memory\benchmark_results\memory_on
```

所有报告都保存在 `tests/benchmarks/memory/benchmark_results/<label>/`，包括 CSV、场景 JSON、模型输出和内存状态。此结果目录已被本地 `.gitignore` 忽略，不会混入远程代码。

**评分限制**：Chat 的 `heuristic_score_0_2` 只是关键词覆盖率，可能因为否定、人物归属和同义改写而误判；Rehearsal 的自动统计只反映记忆检索/使用情况，并**不是**剧情一致性得分。真实质量差异要检查 `rehearsal_jobs.json` 和 `rehearsal_scene.json`。单次 A/B 不具有统计显著性，最好重复多组并保持模型设置不变。

## 6. 免费自检

```powershell
py -3.12 .\tests\benchmarks\memory\selftest.py
```

只检查测试脚本内部工具函数，不调用模型、不收取 API 费用。

## 常见错误

- `401`：本地登录信息缺失或密码错误。
- `503`：LLM 未配置好，或数据库不可用。
- 任务超时：添加 `--job-timeout 600` 增加排演生成的等待上限。
- 相同 `--label` 无法重复使用：改成新的名称，例如 `memory_on_2`。
- 本测试程序**不自动删除**创建的角色/场景，请尽量使用独立测试数据库。
