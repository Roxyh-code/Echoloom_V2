# 排演记忆实验：Mem0 开关

此功能仅作用于非 Demo 的 `/rehearsal` 表演生成。默认关闭；关闭时不导入
Mem0、不初始化记忆存储，也不发起记忆模型请求。原有上下文和一致性审查开关保留。
角色创建、Creator、Companion、方向建议和回顾接口不接入 Mem0。

## 安装与启用

停止后端和前端并备份原来的 `.env`、`work/`。在项目根目录、原有 Python
3.12 虚拟环境中执行：

```bash
python -m pip install -e ".[memory]"
```

该 extra 固定 `mem0ai==2.2.1`。不需要 Mem0 托管账号、Docker、Neo4j 或额外
Mem0 服务。第一版只支持 OpenAI `text-embedding-3-small` 的 1536 维向量。
需要复现实测依赖组合时，可使用 `requirements-memory.lock`（替代开发 lock，
不是要求同时安装两份 lock）；它包含本轮 Linux/Python 3.12 验证过的后端、开发及
记忆依赖，Windows 上的安装仍需本地确认。
在已有 `.env` 中加入：

```dotenv
MEMORY_ENABLED=true
MEMORY_DIRECTORY=work/memory
MEMORY_LLM_MODEL=gpt-4.1-mini
MEMORY_EMBEDDING_MODEL=text-embedding-3-small
MEMORY_TOP_K=5
MEMORY_CONTEXT_BYTES=3000
MEMORY_TIMEOUT_SECONDS=15
MEMORY_INDEX_BATCH_SIZE=4
```

沿用现有 `LLM_API_KEY`，记忆调用明确使用 `https://api.openai.com/v1`；原有
生成模型继续由 `LLM_MODEL` 控制。无需把密钥放到前端或发给别人。重新启动后端，
仍按原来的方式使用排演页面。没有前端新开关。恢复 A 组只需设
`MEMORY_ENABLED=false` 并重启；不要在未完成任务的重试之间切换实验配置。

## 记忆来源和作用范围

这一版刻意使用明确来源的事件记忆，而不是让 Mem0 自由扫描整个数据库：

- 只提取**已正式保存**的场景状态记录（事实、信念、目标、关系、未解线索）。
- 记录必须有 `source_node`、仍存在的 `source_block` 和明确的 `known_by`。
- 无 `known_by` 的内容、角色私聊、角色完整档案、作者笔记、未采用候选和未来导演
  指令不写入记忆。初始角色知识仍走原有上下文，不额外提取。
- 每个来源记录、角色都有独立 Mem0 `run_id`。用户与场景构成隔离范围，角色使用
  `agent_id`，所以提取时也不会看到其他分支、其他记录或其他角色的记忆。
- 来源指纹包含角色映射、原始记录、来源段落内容和模型配置。检索之前重新从
  **当前版本有效历史**计算允许的指纹，支持分支继承共同祖先；不是只按版本 ID 过滤。
- 检索后再次验证用户、角色、run 和来源指纹；返回给生成器的每条记忆保留类型、
  `known_by`、来源节点和段落以及原始状态记录，不能仅凭摘要升级角色知识。

因此不是每个生成段落都会产生记忆：模型没有输出带明确知情角色的状态变化时，
本版不补猜。它比较的是“现有上下文 + Mem0 检索已确认角色事件”的增量效果，
不是全量散文记忆或跨场景记忆系统。`known_by` 本身来自现有生成及验证逻辑，
模型是否正确分配知情范围、是否在生成时遵守它，仍需实际语义评估。

## 数据流与 checkpoint

```text
读取当前场景、版本、操作
  → 检索当前历史允许的角色记忆（必要时补建最多 4 个来源）
  → LangGraph 保存 memory_context checkpoint
  → 整理上下文、生成、校验、可选一致性审查/修复
  → 逐段正式提交场景
  → 将已提交来源写入本地待处理索引日志
  → 单个后台线程调用 Mem0 提取与存储
```

原有最近/较早历史保留。记忆最多占 `MEMORY_CONTEXT_BYTES` 字节；总上下文不足
时先丢弃检索记忆，再沿用原有历史裁剪逻辑。生成和一致性审查看到同一份记忆。
重试从 checkpoint 复用检索结果，不在生成中途重新检索。实验配置变化会阻止
复用不兼容 checkpoint，应发起新操作。

索引使用独立 `index.sqlite` 日志，正式场景提交不会因 Mem0 失败而回滚。已有来源
不会重复提取；提取中断留下的部分向量会在重试该来源前清除。服务重启后，下次
操作只补建当前历史仍然有效的 pending 来源，不主动回放已删场景。场景提交与
日志之间即使中断，下次检索也可从业务历史重建待处理来源。

记忆检索超时或服务异常时沿用原有上下文，任务标记为降级；索引失败保持 pending，
以后操作再尝试。超时不会强制终止已经发出的 OpenAI 请求，后台可能继续产生用量。

## 存储与备份

默认相对于后端启动工作目录解析为绝对路径：

```text
work/memory/
  index.sqlite       # 来源 payload 和 pending/ready 状态
  history.sqlite     # Mem0 变更及提取历史
  qdrant/            # 记忆向量及 metadata
  internal/          # Mem0 本地辅助文件
```

原有业务数据库和 LangGraph checkpoint 不变，不需要新的 Alembic migration。
记忆目录也包含故事数据，不要提交到 Git。停服后将整个目录一起备份。
本地 Qdrant 仅支持一个后端进程持有此目录，继续使用现有单 worker 启动方式。

编辑、切换分支或删除后，旧来源不再被检索；**旧向量和日志仍保留在磁盘**，这属于
逻辑失效，不是物理擦除。需要清空实验记忆时，先停服，再删除专用记忆目录并重启，
不要删除原有 `work/echoloom.db` 或 portraits。下一次启用会按当前历史逐步重建。

## 观察实验结果

`GET /api/rehearsal/jobs/{id}` 新增 `memory` 字段：

- `status`: `disabled`、`empty`、`ok`、`partial` 或 `degraded`。
- `items`: 检索到且通过来源验证的记忆及证据，只向任务所属用户返回。
- `used_ids`: 经过上下文预算裁剪后，实际给生成模型的记忆 ID。
- `pending_sources`: 尚未成功索引的来源数量（适用时）。
- `elapsed_ms`、`error_type`: 检索耗时和安全错误类型（适用时）。

Demo 不调用 Mem0，状态报告为 disabled。服务器只记录状态、数量、耗时和错误类型，
不记录提取提示词或原始 SDK 错误。当前没有完整 token/费用计量；记忆提取及向量
请求会增加 OpenAI 费用。Mem0 的变更/关联行为与此前人工更新逻辑不同，不应混淆。

第一次没有历史时返回 empty；刚启用、索引仍在进行时可能 partial/degraded。
比较质量时要同时记录实际使用的记忆和这些状态，避免把降级样本当作正常 B 组。
先固定一致性审查开关和生成模型，使用相同初始场景与操作脚本，做长程约定、秘密、
信念纠正、编辑和分支隔离对照。不要仅凭一组样例声称改善了长期记忆质量。

## 自动检查

```bash
python -m pip install -e ".[dev,memory]"
python -m pytest -q tests/mvp/test_rehearsal_memory.py
```

自动检查使用模拟模型；另有真实 Mem0/Qdrant SDK 测试，仅替换网络模型响应和向量。
不使用生产密钥，也不产生付费 API 请求。真实模型提取质量和整体体验需本地验证。
