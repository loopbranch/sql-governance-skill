# 规范抽取与公开边界

本规则库依据用户提供的《KooWork SQL编程规范》抽取。附件是参考材料，不是对执行代理的额外指令；实际行为由 `SKILL.md` 与结构化规则定义。

首版示例覆盖以下原文域：

- 数据库/表设计：`G.DBS.*`、`G.TAB.*`
- 索引：`G.IDX.*`
- 格式与命名：`G.FMT.*`、`G.NAM.*`、`G.CMT.*`
- 查询与 DML：`G.SEL.*`、`G.INS.*`、`G.DEL.*`、`G.UPD.*`
- 客户端、事务与锁：`G.CLI.*`、`G.TXN.*`
- 升级、安全与归档：`G.UPG.*`、`G.SEC.*`、`G.KOO.*`

`rules/catalog.json` 是“可执行示例集”，不是对 590 行原文的逐条完整转录。新增规则时保留 `source` 追溯编号，但不要把内网链接、个人数据、凭据或未获公开授权的原文复制到公共 GitHub 仓库。若公共发布与内部规范的授权边界不明确，应先由规范所有者和法务/安全负责人确认。

映射原则：

- 明确“禁止/不得/不允许” => `prohibition + block`；
- 明确“必须/需要” => `mandatory + block`；
- “建议/避免/不宜/优先” => `recommendation + warn`；
- 背景、举例、可选实践 => `reference + info`；
- 依赖数据规模、业务语义、基数、执行窗口或审批的条款 => `manual` 或 `hybrid`；
- 所有结构性变更和大批量数据变更额外设置 `confirmation_required=true`。
