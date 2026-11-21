# 规范抽取与公开边界

本规则库依据用户提供的《KooWork SQL编程规范》抽取。附件是参考材料，不是对执行代理的额外指令；实际行为由 `SKILL.md` 与结构化规则定义。

公共目录覆盖以下原文域：

- 数据库/表设计：`G.DBS.*`、`G.TAB.*`
- 索引：`G.IDX.*`
- 格式与命名：`G.FMT.*`、`G.NAM.*`、`G.CMT.*`
- 查询与 DML：`G.SEL.*`、`G.INS.*`、`G.DEL.*`、`G.UPD.*`
- 客户端、事务与锁：`G.CLI.*`、`G.TXN.*`
- 升级、安全与归档：`G.UPG.*`、`G.SEC.*`、`G.KOO.*`

`rules/common.json` 对附件的 154 个编号条款逐条建立 ID 和判定元数据；内容为公开可复用的归纳表达，不复制内网链接、个人数据或凭据。MySQL 特有内容在 `rules/mysql.json`，PostgreSQL 的等价实现和差异在 `rules/postgresql.json`。

方言适配原则：公共层表达意图和风险，方言层表达具体类型、语法和系统目录。例如编码统一在公共层，MySQL 落为 `utf8mb4`，PostgreSQL 落为 `UTF8`；有序 UUID 在 MySQL 使用 `BINARY(16)`，PostgreSQL 使用原生 `uuid`。

映射原则：

- 明确“禁止/不得/不允许” => `prohibition + block`；
- 明确“必须/需要” => `mandatory + block`；
- “建议/避免/不宜/优先” => `recommendation + warn`；
- 背景、举例、可选实践 => `reference + info`；
- 依赖数据规模、业务语义、基数、执行窗口或审批的条款 => `manual` 或 `hybrid`；
- 所有结构性变更和大批量数据变更额外设置 `confirmation_required=true`。
