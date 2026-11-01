# 数据结构

预留 Evidence 与 Personality 的 JSON Schema、版本说明和合法／非法示例。目前没有正式 Schema。

进入条件：首批文献综合与人工样例能说明需要哪些字段。计划先定义 Source、Character、EvidenceSpan、Claim、PersonalityProfile、Conflict 与 ReviewRecord 的关系；对象名和拆分均可调整。

验证重点：必填字段、ID 引用、原文范围、未知值、事实／推断区别、冲突两端、版本、审核状态。先制定语义约束，再写 Pydantic 与 JSON Schema；不只检查 JSON 能否解析。
