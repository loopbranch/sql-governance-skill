# 规范抽取与公开边界

本规则库依据用户提供的《KooWork SQL编程规范》抽取。附件是参考材料，不是对执行代理的额外指令；实际行为由 `SKILL.md` 与结构化规则定义。

每个方言加载路径覆盖以下原文域：

- 数据库/表设计：`G.DBS.*`、`G.TAB.*`
- 索引：`G.IDX.*`
- 格式与命名：`G.FMT.*`、`G.NAM.*`、`G.CMT.*`
- 查询与 DML：`G.SEL.*`、`G.INS.*`、`G.DEL.*`、`G.UPD.*`
- 客户端、事务与锁：`G.CLI.*`、`G.TXN.*`
- 升级、安全与归档：`G.UPG.*`、`G.SEC.*`、`G.KOO.*`

154 个编号条款通过 `source` 逐条追溯。无方言差异的条款放在 `rules/common.json`；存在任一语法、语义、类型、版本或整改差异的条款，必须在 `rules/mysql.json` 和 `rules/postgresql.json` 各保存一条规则。内容为公开可复用的归纳表达，不复制内网链接、个人数据或凭据。

方言适配原则：差异规则不保留公共抽象占位。例如编码、schema、标识符长度、注释、JOIN、DML 子句、赋值语义、锁、字段变更和在线 DDL 均直接拆成 MySQL/PostgreSQL 两条规则。语法事实来源见 [dialect-spec-sources.md](dialect-spec-sources.md)。

映射原则：

层级判定读取条款标题及其说明正文；若源条款把强制项和建议项混写，自动 Block 只覆盖明确强制部分，建议部分另作人工执行计划评审。

- 明确“禁止/不得/不允许” => `prohibition + block`；
- 明确“必须/需要” => `mandatory + block`；
- “建议/避免/不宜/优先” => `recommendation + warn`；
- 背景、举例、可选实践 => `reference + info`；
- 依赖数据规模、业务语义、基数、执行窗口或审批的条款 => `manual` 或 `hybrid`；
- 所有结构性变更和大批量数据变更额外设置 `confirmation_required=true`。
